"""
Moteur de validation des contraintes dures.

Chaque fonction vérifie UNE contrainte métier.
En cas de violation, elle lève une ValidationError avec un message explicite.
La fonction principale `validate_assignment` orchestre toutes les vérifications.
"""

from datetime import timedelta, datetime
from decimal import Decimal

from django.db.models import Q, Sum, F
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .models import (
    Staff, Shift, ShiftAssignment, Absence,
    Contract, StaffCertification, Rule, Preference,
    ShiftRequiredCertification,
)


class ConstraintViolation:
    """Encapsule une violation de contrainte avec code et message."""

    def __init__(self, code: str, message: str, details: dict = None):
        self.code = code
        self.message = message
        self.details = details or {}

    def to_dict(self):
        return {
            'code': self.code,
            'message': self.message,
            'details': self.details,
        }


def get_rule_value(rule_type: str, reference_date=None) -> Decimal:
    """
    Récupère la valeur d'une règle métier depuis la table `rule`.
    Prend la règle active à la date de référence.
    """
    if reference_date is None:
        reference_date = timezone.now().date()

    rule = Rule.objects.filter(
        rule_type=rule_type,
        valid_from__lte=reference_date
    ).filter(
        Q(valid_to__gte=reference_date) | Q(valid_to__isnull=True)
    ).order_by('-valid_from').first()

    if rule is None:
        # Valeurs par défaut de sécurité si la règle n'existe pas en base
        defaults = {
            'max_weekly_hours': Decimal('48'),
            'min_rest_hours': Decimal('11'),
            'max_consecutive_nights': Decimal('3'),
            'max_weekend_per_month': Decimal('2'),
        }
        return defaults.get(rule_type, Decimal('0'))

    return rule.value


# ─────────────────────────────────────────────
# CONTRAINTE 1 : Pas de chevauchement horaire
# ─────────────────────────────────────────────

def check_no_time_overlap(staff: Staff, shift: Shift) -> list:
    """
    Un soignant ne peut pas être affecté à deux postes dont
    les plages horaires se chevauchent, même partiellement.
    """
    violations = []

    overlapping = ShiftAssignment.objects.filter(
        staff=staff
    ).filter(
        shift__start_datetime__lt=shift.end_datetime,
        shift__end_datetime__gt=shift.start_datetime,
    ).select_related('shift', 'shift__shift_type', 'shift__care_unit')

    if overlapping.exists():
        conflicting = overlapping.first()
        violations.append(ConstraintViolation(
            code='TIME_OVERLAP',
            message=(
                f"{staff} est déjà affecté(e) à une garde qui chevauche "
                f"ce créneau : {conflicting.shift.shift_type.name} "
                f"({conflicting.shift.start_datetime.strftime('%d/%m %H:%M')} — "
                f"{conflicting.shift.end_datetime.strftime('%H:%M')}) "
                f"dans {conflicting.shift.care_unit}."
            ),
            details={
                'conflicting_shift_id': conflicting.shift.id,
                'conflicting_start': str(conflicting.shift.start_datetime),
                'conflicting_end': str(conflicting.shift.end_datetime),
            }
        ))

    return violations


# ─────────────────────────────────────────────
# CONTRAINTE 2 : Certifications valides
# ─────────────────────────────────────────────

def check_certifications(staff: Staff, shift: Shift) -> list:
    """
    Le soignant doit posséder TOUTES les certifications requises
    par le poste, et aucune ne doit être expirée à la date de la garde.
    """
    violations = []
    shift_date = shift.start_datetime.date()

    required_certs = ShiftRequiredCertification.objects.filter(
        shift=shift
    ).values_list('certification_id', flat=True)

    if not required_certs:
        return violations  # Pas de certification requise

    for cert_id in required_certs:
        # Vérifier que le soignant possède cette certification
        # et qu'elle n'est pas expirée
        staff_cert = StaffCertification.objects.filter(
            staff=staff,
            certification_id=cert_id,
            obtained_date__lte=shift_date,
        ).filter(
            Q(expiration_date__gte=shift_date) | Q(expiration_date__isnull=True)
        ).first()

        if staff_cert is None:
            # Soit le soignant ne l'a pas, soit elle est expirée
            from .models import Certification
            cert_name = Certification.objects.get(id=cert_id).name

            # Vérifier si elle est expirée vs jamais obtenue
            expired = StaffCertification.objects.filter(
                staff=staff,
                certification_id=cert_id,
                expiration_date__lt=shift_date,
            ).exists()

            if expired:
                msg = (
                    f"La certification « {cert_name} » de {staff} est expirée. "
                    f"Elle doit être renouvelée avant le {shift_date}."
                )
            else:
                msg = (
                    f"{staff} ne possède pas la certification « {cert_name} » "
                    f"requise pour ce poste."
                )

            violations.append(ConstraintViolation(
                code='MISSING_CERTIFICATION',
                message=msg,
                details={
                    'certification_id': cert_id,
                    'certification_name': cert_name,
                    'expired': expired,
                }
            ))

    return violations


# ─────────────────────────────────────────────
# CONTRAINTE 3 : Repos minimum après garde de nuit
# ─────────────────────────────────────────────

def check_rest_after_night(staff: Staff, shift: Shift) -> list:
    """
    Après une garde de nuit, un repos minimal réglementaire
    doit être respecté avant toute nouvelle affectation.
    """
    violations = []
    min_rest_hours = float(get_rule_value('min_rest_hours', shift.start_datetime.date()))

    # Chercher la dernière garde AVANT ce créneau
    previous_assignment = ShiftAssignment.objects.filter(
        staff=staff,
        shift__end_datetime__lte=shift.start_datetime,
    ).select_related(
        'shift', 'shift__shift_type'
    ).order_by('-shift__end_datetime').first()

    if previous_assignment:
        prev_shift = previous_assignment.shift
        # Vérifier si la garde précédente nécessite un repos
        if prev_shift.shift_type.requires_rest_after:
            rest_duration = (
                shift.start_datetime - prev_shift.end_datetime
            ).total_seconds() / 3600

            if rest_duration < min_rest_hours:
                violations.append(ConstraintViolation(
                    code='INSUFFICIENT_REST',
                    message=(
                        f"Repos insuffisant pour {staff}. "
                        f"La garde précédente ({prev_shift.shift_type.name}) "
                        f"se terminait à {prev_shift.end_datetime.strftime('%d/%m %H:%M')}. "
                        f"Repos effectif : {rest_duration:.1f}h. "
                        f"Repos minimum requis : {min_rest_hours}h."
                    ),
                    details={
                        'previous_shift_id': prev_shift.id,
                        'previous_end': str(prev_shift.end_datetime),
                        'rest_hours': round(rest_duration, 1),
                        'required_rest_hours': min_rest_hours,
                    }
                ))

    # Chercher aussi la prochaine garde APRÈS ce créneau
    # (si on insère une garde au milieu)
    next_assignment = ShiftAssignment.objects.filter(
        staff=staff,
        shift__start_datetime__gte=shift.end_datetime,
    ).select_related(
        'shift', 'shift__shift_type'
    ).order_by('shift__start_datetime').first()

    if next_assignment and shift.shift_type.requires_rest_after:
        next_shift = next_assignment.shift
        rest_duration = (
            next_shift.start_datetime - shift.end_datetime
        ).total_seconds() / 3600

        if rest_duration < min_rest_hours:
            violations.append(ConstraintViolation(
                code='INSUFFICIENT_REST_BEFORE_NEXT',
                message=(
                    f"L'ajout de cette garde ne laisserait pas "
                    f"assez de repos avant la garde suivante de {staff} "
                    f"({next_shift.shift_type.name} à "
                    f"{next_shift.start_datetime.strftime('%d/%m %H:%M')}). "
                    f"Repos : {rest_duration:.1f}h / {min_rest_hours}h requis."
                ),
                details={
                    'next_shift_id': next_shift.id,
                    'rest_hours': round(rest_duration, 1),
                    'required_rest_hours': min_rest_hours,
                }
            ))

    return violations


# ─────────────────────────────────────────────
# CONTRAINTE 4 : Seuil de sécurité du service
# ─────────────────────────────────────────────

def check_min_staff_threshold(shift: Shift) -> list:
    """
    Vérifie que le nombre max de soignants n'est pas dépassé.
    Note : cette contrainte vérifie le max_staff, pas le min_staff
    (le min_staff est vérifié à la génération du planning, pas à l'affectation).
    """
    violations = []

    if shift.max_staff is not None:
        current_count = ShiftAssignment.objects.filter(shift=shift).count()
        if current_count >= shift.max_staff:
            violations.append(ConstraintViolation(
                code='MAX_STAFF_REACHED',
                message=(
                    f"Le créneau {shift} a atteint sa capacité maximale "
                    f"({shift.max_staff} soignants). "
                    f"Affectations actuelles : {current_count}."
                ),
                details={
                    'current_count': current_count,
                    'max_staff': shift.max_staff,
                }
            ))

    return violations


# ─────────────────────────────────────────────
# CONTRAINTE 5 : Type de contrat autorise la garde
# ─────────────────────────────────────────────

def check_contract_allows_shift(staff: Staff, shift: Shift) -> list:
    """
    Le contrat actif du soignant doit autoriser ce type de garde.
    Ex : un stagiaire ne peut pas faire de nuit.
    """
    violations = []
    shift_date = shift.start_datetime.date()

    # Trouver le contrat actif
    active_contract = Contract.objects.filter(
        staff=staff,
        start_date__lte=shift_date,
    ).filter(
        Q(end_date__gte=shift_date) | Q(end_date__isnull=True)
    ).select_related('contract_type').order_by('-start_date').first()

    if active_contract is None:
        violations.append(ConstraintViolation(
            code='NO_ACTIVE_CONTRACT',
            message=(
                f"{staff} n'a pas de contrat actif à la date du "
                f"{shift_date}. Impossible de l'affecter."
            ),
            details={'shift_date': str(shift_date)}
        ))
        return violations

    # Vérifier si le type de garde est autorisé
    contract_type = active_contract.contract_type

    # Vérifier les gardes de nuit
    is_night_shift = shift.shift_type.name.lower() in ['nuit', 'garde de nuit', 'night']
    if is_night_shift and not contract_type.night_shift_allowed:
        violations.append(ConstraintViolation(
            code='NIGHT_SHIFT_NOT_ALLOWED',
            message=(
                f"Le contrat de {staff} ({contract_type.name}) "
                f"n'autorise pas les gardes de nuit."
            ),
            details={
                'contract_type': contract_type.name,
                'contract_id': active_contract.id,
            }
        ))

    return violations


# ─────────────────────────────────────────────
# CONTRAINTE 6 : Pas d'affectation pendant une absence
# ─────────────────────────────────────────────

def check_no_absence(staff: Staff, shift: Shift) -> list:
    """
    Un soignant en absence déclarée ne peut pas être affecté.
    """
    violations = []
    shift_start = shift.start_datetime.date()
    shift_end = shift.end_datetime.date()

    # Une absence couvre la période si elle commence avant la fin
    # du shift ET se termine après le début du shift
    absences = Absence.objects.filter(
        staff=staff,
        start_date__lte=shift_end,
    ).filter(
        # Utiliser actual_end_date si disponible, sinon expected_end_date
        Q(actual_end_date__gte=shift_start) |
        (Q(actual_end_date__isnull=True) & Q(expected_end_date__gte=shift_start))
    ).select_related('absence_type')

    if absences.exists():
        absence = absences.first()
        end = absence.actual_end_date or absence.expected_end_date
        violations.append(ConstraintViolation(
            code='STAFF_ABSENT',
            message=(
                f"{staff} est en absence ({absence.absence_type.name}) "
                f"du {absence.start_date} au {end}. "
                f"Impossible de l'affecter le {shift_start}."
            ),
            details={
                'absence_id': absence.id,
                'absence_type': absence.absence_type.name,
                'absence_start': str(absence.start_date),
                'absence_end': str(end),
            }
        ))

    return violations


# ─────────────────────────────────────────────
# CONTRAINTE 7 : Quota d'heures hebdomadaires
# ─────────────────────────────────────────────

def check_weekly_hours_quota(staff: Staff, shift: Shift) -> list:
    """
    Le quota d'heures hebdomadaires contractuelles ne peut pas être dépassé.
    Le quota est ajusté selon le pourcentage du contrat (workload_percent).
    """
    violations = []
    shift_date = shift.start_datetime.date()

    # Trouver le contrat actif
    active_contract = Contract.objects.filter(
        staff=staff,
        start_date__lte=shift_date,
    ).filter(
        Q(end_date__gte=shift_date) | Q(end_date__isnull=True)
    ).select_related('contract_type').order_by('-start_date').first()

    if not active_contract:
        return violations  # Déjà vérifié dans check_contract_allows_shift

    max_hours_base = active_contract.contract_type.max_hours_per_week
    if max_hours_base is None:
        max_hours_base = float(get_rule_value('max_weekly_hours', shift_date))

    # Ajuster selon le pourcentage de temps de travail
    max_hours = max_hours_base * (active_contract.workload_percent / 100.0)

    # Calculer les heures de la semaine ISO du shift
    # Trouver le lundi et le dimanche de la semaine
    day_of_week = shift_date.weekday()  # 0=Lundi
    week_start = shift_date - timedelta(days=day_of_week)
    week_end = week_start + timedelta(days=6)

    # Heures déjà affectées cette semaine
    week_assignments = ShiftAssignment.objects.filter(
        staff=staff,
        shift__start_datetime__date__gte=week_start,
        shift__start_datetime__date__lte=week_end,
    ).select_related('shift')

    total_hours = sum(
        (a.shift.end_datetime - a.shift.start_datetime).total_seconds() / 3600
        for a in week_assignments
    )

    # Ajouter les heures de la garde proposée
    new_shift_hours = (
        shift.end_datetime - shift.start_datetime
    ).total_seconds() / 3600
    projected_total = total_hours + new_shift_hours

    if projected_total > max_hours:
        violations.append(ConstraintViolation(
            code='WEEKLY_HOURS_EXCEEDED',
            message=(
                f"L'affectation de {staff} porterait son total hebdomadaire à "
                f"{projected_total:.1f}h (semaine du {week_start} au {week_end}). "
                f"Maximum autorisé : {max_hours:.0f}h "
                f"({active_contract.workload_percent}% de {max_hours_base}h)."
            ),
            details={
                'current_hours': round(total_hours, 1),
                'new_shift_hours': round(new_shift_hours, 1),
                'projected_total': round(projected_total, 1),
                'max_hours': max_hours,
                'workload_percent': active_contract.workload_percent,
            }
        ))

    return violations


# ─────────────────────────────────────────────
# CONTRAINTE 8 : Contraintes impératives déclarées
# ─────────────────────────────────────────────

def check_hard_preferences(staff: Staff, shift: Shift) -> list:
    """
    Les contraintes impératives déclarées par le soignant (F-07)
    doivent être respectées.
    """
    violations = []
    shift_date = shift.start_datetime.date()
    shift_day_of_week = shift_date.weekday()  # 0=Lundi, 6=Dimanche

    hard_constraints = Preference.objects.filter(
        staff=staff,
        is_hard_constraint=True,
        start_date__lte=shift_date,
    ).filter(
        Q(end_date__gte=shift_date) | Q(end_date__isnull=True)
    )

    for constraint in hard_constraints:
        violated = False

        # Contrainte sur un jour de la semaine
        if constraint.day_of_week is not None:
            if constraint.day_of_week == shift_day_of_week:
                violated = True

        # Contrainte sur un type de garde
        if constraint.shift_type_id is not None:
            if constraint.shift_type_id == shift.shift_type_id:
                violated = True

        # Si ni jour ni type n'est spécifié, c'est une contrainte
        # générale sur la période — on la considère violée
        if constraint.day_of_week is None and constraint.shift_type_id is None:
            violated = True

        if violated:
            violations.append(ConstraintViolation(
                code='HARD_PREFERENCE_VIOLATED',
                message=(
                    f"Contrainte impérative violée pour {staff} : "
                    f"« {constraint.description} » "
                    f"(valide du {constraint.start_date} au "
                    f"{constraint.end_date or 'indéterminé'})."
                ),
                details={
                    'preference_id': constraint.id,
                    'description': constraint.description,
                    'day_of_week': constraint.day_of_week,
                    'shift_type_id': constraint.shift_type_id,
                }
            ))

    return violations


# ═══════════════════════════════════════════════
# FONCTION PRINCIPALE — Orchestration
# ═══════════════════════════════════════════════

def validate_assignment(staff_id: int, shift_id: int) -> list:
    """
    Valide une affectation en vérifiant TOUTES les contraintes dures.

    Returns:
        Liste de ConstraintViolation. Si vide, l'affectation est autorisée.
    """
    try:
        staff = Staff.objects.get(id=staff_id)
    except Staff.DoesNotExist:
        return [ConstraintViolation(
            'STAFF_NOT_FOUND',
            f"Aucun soignant trouvé avec l'id {staff_id}."
        )]

    try:
        shift = Shift.objects.select_related(
            'shift_type', 'care_unit', 'care_unit__service'
        ).get(id=shift_id)
    except Shift.DoesNotExist:
        return [ConstraintViolation(
            'SHIFT_NOT_FOUND',
            f"Aucun créneau de garde trouvé avec l'id {shift_id}."
        )]

    # Vérifier que le soignant est actif
    if not staff.is_active:
        return [ConstraintViolation(
            'STAFF_INACTIVE',
            f"{staff} est inactif et ne peut pas être affecté."
        )]

    # Exécuter toutes les vérifications
    all_violations = []
    all_violations.extend(check_no_absence(staff, shift))
    all_violations.extend(check_contract_allows_shift(staff, shift))
    all_violations.extend(check_no_time_overlap(staff, shift))
    all_violations.extend(check_certifications(staff, shift))
    all_violations.extend(check_rest_after_night(staff, shift))
    all_violations.extend(check_min_staff_threshold(shift))
    all_violations.extend(check_weekly_hours_quota(staff, shift))
    all_violations.extend(check_hard_preferences(staff, shift))

    return all_violations