"""
Phase 3 - Moteur de Génération de Planning
Heuristique gloutonne avec scoring des contraintes molles
"""

from datetime import timedelta, date
from collections import defaultdict
from django.db.models import Count
from django.utils import timezone
from core.models import (
    Shift, ShiftAssignment, Staff, Rule, Preference,
    StaffServiceAssignment
)
from core.validators import validate_assignment


class PlanningGenerator:
    """
    Génère un planning automatique en minimisant les contraintes molles
    tout en respectant les contraintes dures.
    """
    
    # Poids des pénalités (paramétrables)
    WEIGHTS = {
        'consecutive_nights': 25,    # Nuits consécutives excessives
        'preferences': 30,           # Non-respect préférences
        'workload_balance': 20,      # Déséquilibre de charge
        'service_change': 10,        # Changement de service
        'weekend': 15                # Week-end non équitable
    }

    def __init__(self):
        self.assignments_created = []
        self.total_soft_score = 0
        self.uncovered_shifts = 0
        self.penalties_detail = defaultdict(int)

    def generate(self, start_date, end_date, service_id=None):
        """
        Génère le planning pour une période donnée.
        
        Args:
            start_date: Date de début (string ou date)
            end_date: Date de fin (string ou date)
            service_id: ID du service (optionnel)
        
        Returns:
            dict avec le planning et les métriques
        """
        # Conversion des dates
        if isinstance(start_date, str):
            start_date = date.fromisoformat(start_date)
        if isinstance(end_date, str):
            end_date = date.fromisoformat(end_date)

        # Récupérer les shifts à couvrir
        shifts = Shift.objects.filter(
            start_datetime__date__gte=start_date,
            start_datetime__date__lte=end_date
        ).select_related('care_unit', 'care_unit__service', 'shift_type').order_by('start_datetime')

        if service_id:
            shifts = shifts.filter(care_unit__service_id=service_id)

        # Charger les données utiles
        self._load_context(start_date, end_date)

        # Parcourir chaque créneau
        for shift in shifts:
            best_staff = self._find_best_candidate(shift)
            
            if best_staff:
                # Créer l'affectation
                assignment = ShiftAssignment.objects.create(
                    shift=shift,
                    staff=best_staff
                )
                self.assignments_created.append(assignment)
                
                # Mettre à jour le contexte
                self._update_context(best_staff, shift)
            else:
                self.uncovered_shifts += 1

        return self._build_result(shifts.count())

    def _load_context(self, start_date, end_date):
        """Charge les données de contexte pour le scoring"""
        self.existing_assignments = list(ShiftAssignment.objects.filter(
            shift__start_datetime__date__gte=start_date,
            shift__start_datetime__date__lte=end_date
        ).select_related('staff', 'shift', 'shift__shift_type'))

        # Compter les gardes par soignant
        self.staff_workload = defaultdict(int)
        for a in self.existing_assignments:
            self.staff_workload[a.staff_id] += 1

        # Charger les règles
        self.max_consecutive_nights = self._get_rule('max_consecutive_nights', 3)
        self.max_weekend_per_month = self._get_rule('max_weekend_per_month', 2)

    def _get_rule(self, rule_type, default):
        """Récupère une règle depuis la base"""
        from core.models import Rule
        rule = Rule.objects.filter(rule_type=rule_type).first()
        return float(rule.value) if rule else default

    def _find_best_candidate(self, shift):
        """
        Trouve le meilleur soignant pour un shift donné.
        Utilise une heuristique gloutonne avec scoring.
        """
        # 1. Filtrer les soignants éligibles (contraintes dures)
        eligible_staff = []
        for staff in Staff.objects.filter(is_active=True):
            violations = validate_assignment(staff.id, shift.id)
            if not violations:
                eligible_staff.append(staff)

        if not eligible_staff:
            return None

        # 2. Calculer le score pour chaque candidat
        best_staff = None
        best_score = float('inf')

        for staff in eligible_staff:
            score = self._calculate_soft_score(staff, shift)
            
            if score < best_score:
                best_score = score
                best_staff = staff

        self.total_soft_score += best_score
        return best_staff

    def _calculate_soft_score(self, staff, shift):
        """Calcule le score de pénalités pour un soignant"""
        score = 0

        # 1. Pénalité nuits consécutives
        score += self._penalty_consecutive_nights(staff, shift) * self.WEIGHTS['consecutive_nights']

        # 2. Pénalité préférences
        score += self._penalty_preferences(staff, shift) * self.WEIGHTS['preferences']

        # 3. Pénalité équilibre de charge
        score += self._penalty_workload(staff) * self.WEIGHTS['workload_balance']

        # 4. Pénalité changement de service
        score += self._penalty_service_change(staff, shift) * self.WEIGHTS['service_change']

        # 5. Pénalité week-end
        score += self._penalty_weekend(staff, shift) * self.WEIGHTS['weekend']

        return score

    def _penalty_consecutive_nights(self, staff, shift):
        """Pénalité si le soignant fait trop de nuits consécutives"""
        # Logique simplifiée : vérifier les nuits précédentes
        shift_date = shift.start_datetime.date()
        
        # Chercher les nuits dans les 3 jours précédents
        night_shifts = [a for a in self.existing_assignments 
                       if a.staff_id == staff.id 
                       and a.shift.shift_type.name.lower().find('nuit') >= 0
                       and (shift_date - a.shift.start_datetime.date()).days <= 3]
        
        if len(night_shifts) >= self.max_consecutive_nights:
            return 50
        return 0

    def _penalty_preferences(self, staff, shift):
        """Pénalité si on ne respecte pas les préférences du soignant"""
        shift_date = shift.start_datetime.date()
        day_of_week = shift_date.weekday()
        
        hard_prefs = Preference.objects.filter(
            staff=staff,
            is_hard_constraint=True,
            start_date__lte=shift_date
        ).filter(
            models.Q(end_date__gte=shift_date) | models.Q(end_date__isnull=True)
        )
        
        for pref in hard_prefs:
            if pref.day_of_week == day_of_week:
                return 100  # Forte pénalité pour contrainte dure non respectée
            if pref.shift_type_id and pref.shift_type_id == shift.shift_type_id:
                return 50
        
        return 0

    def _penalty_workload(self, staff):
        """Pénalité basée sur le déséquilibre de charge"""
        # Plus le soignant a déjà de gardes, plus la pénalité est élevée
        current_load = self.staff_workload.get(staff.id, 0)
        
        # Calculer la moyenne pour comparaison
        if self.staff_workload:
            avg_load = sum(self.staff_workload.values()) / len(self.staff_workload)
            diff = current_load - avg_load
            return max(0, diff * 5)
        return 0

    def _penalty_service_change(self, staff, shift):
        """Pénalité si changement de service dans la semaine"""
        # Logique simplifiée
        return 0

    def _penalty_weekend(self, staff, shift):
        """Pénalité pour les week-ends"""
        day = shift.start_datetime.weekday()
        if day >= 5:  # Samedi ou Dimanche
            # Compter les week-ends déjà travaillé ce mois
            existing_weekends = len([a for a in self.existing_assignments 
                                    if a.staff_id == staff.id 
                                    and a.shift.start_datetime.weekday() >= 5])
            if existing_weekends >= self.max_weekend_per_month:
                return 30
        return 0

    def _update_context(self, staff, shift):
        """Met à jour le contexte après une affectation"""
        self.staff_workload[staff.id] += 1

    def _build_result(self, total_shifts):
        """Construit le résultat à retourner"""
        return {
            "success": self.uncovered_shifts == 0,
            "assignments_count": len(self.assignments_created),
            "total_shifts": total_shifts,
            "uncovered_shifts": self.uncovered_shifts,
            "soft_score": self.total_soft_score,
            "quality_score": max(0, 100 - (self.total_soft_score / 10)),
            "message": self._get_message()
        }

    def _get_message(self):
        if self.uncovered_shifts == 0:
            return "✅ Planning généré avec succès ! Toutes les gardes sont couvertes."
        elif len(self.assignments_created) > 0:
            return f"⚠️ Planning généré avec {self.uncovered_shifts} garde(s) non couverte(s)."
        return "❌ Impossible de générer le planning. Aucune garde n'a pu être couverte."