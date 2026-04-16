"""
Phase 3 - Moteur de Génération Automatique de Planning
Heuristique gloutonne + scoring des contraintes molles
"""

from datetime import timedelta, date
from collections import defaultdict
from django.db.models import Q
from core.models import (
    Shift, ShiftAssignment, Staff, Rule, Preference,
    StaffServiceAssignment, Contract
)
from core.validators import validate_assignment


class PlanningGenerator:
    """
    Génère un planning automatique en :
    1. Respectant les contraintes dures (via validate_assignment)
    2. Minimisant les contraintes molles (via scoring)
    
    Heuristique : pour chaque créneau, on choisit le soignant légal 
    qui a le meilleur score (le plus bas = le mieux)
    """
    
    # Poids des pénalités
    WEIGHTS = {
        'consecutive_nights': 25,
        'preferences': 30,
        'workload_balance': 20,
        'service_change': 10,
        'weekend': 15
    }

    def __init__(self):
        self.assignments_created = []
        self.total_soft_score = 0
        self.uncovered_shifts = 0
        self.penalties_detail = defaultdict(float)
        self.staff_workload = defaultdict(int)
        self.staff_nights = defaultdict(list)
        self.staff_weekends = defaultdict(int)
        self.staff_services = defaultdict(set)

    def generate(self, start_date, end_date, service_id=None):
        """Point d'entrée principal"""
        
        # Conversion des dates
        if isinstance(start_date, str):
            start_date = date.fromisoformat(start_date)
        if isinstance(end_date, str):
            end_date = date.fromisoformat(end_date)

        # Supprimer les anciennes affectations sur cette période
        self._clean_existing_assignments(start_date, end_date, service_id)

        # Récupérer les shifts à couvrir
        shifts = self._get_shifts(start_date, end_date, service_id)

        # Charger le contexte
        self._load_context(start_date, end_date)

        # Trier les shifts : d'abord les plus critiques
        sorted_shifts = self._sort_shifts(shifts)

        # Pour chaque créneau, trouver le meilleur soignant
        for shift in sorted_shifts:
            # Vérifier si le shift a déjà assez de personnel
            current_count = ShiftAssignment.objects.filter(shift=shift).count()
            if current_count >= shift.min_staff:
                continue

            # Remplir jusqu'au minimum requis
            needed = shift.min_staff - current_count
            for _ in range(needed):
                best_staff = self._find_best_candidate(shift)
                
                if best_staff:
                    assignment = ShiftAssignment.objects.create(
                        shift=shift,
                        staff=best_staff
                    )
                    self.assignments_created.append(assignment)
                    self._update_context(best_staff, shift)
                else:
                    self.uncovered_shifts += 1
                    break

        return self._build_result(len(sorted_shifts))

    def _clean_existing_assignments(self, start_date, end_date, service_id):
        """Supprime les affectations existantes sur la période"""
        qs = ShiftAssignment.objects.filter(
            shift__start_datetime__date__gte=start_date,
            shift__start_datetime__date__lte=end_date
        )
        if service_id:
            qs = qs.filter(shift__care_unit__service_id=service_id)
        count = qs.count()
        qs.delete()

    def _get_shifts(self, start_date, end_date, service_id):
        """Récupère les shifts à couvrir"""
        shifts = Shift.objects.filter(
            start_datetime__date__gte=start_date,
            start_datetime__date__lte=end_date
        ).select_related(
            'care_unit', 'care_unit__service', 'shift_type'
        ).order_by('start_datetime')

        if service_id:
            shifts = shifts.filter(care_unit__service_id=service_id)

        return list(shifts)

    def _sort_shifts(self, shifts):
        """
        Trie les shifts par priorité :
        1. Services les plus critiques d'abord
        2. Nuits avant les jours (plus difficiles à couvrir)
        """
        def priority(shift):
            criticality = -shift.care_unit.service.criticality_level
            is_night = 0 if 'nuit' in shift.shift_type.name.lower() else 1
            return (criticality, is_night, shift.start_datetime)
        
        return sorted(shifts, key=priority)

    def _load_context(self, start_date, end_date):
        """Charge les données de contexte"""
        existing = ShiftAssignment.objects.filter(
            shift__start_datetime__date__gte=start_date,
            shift__start_datetime__date__lte=end_date
        ).select_related('staff', 'shift', 'shift__shift_type', 'shift__care_unit')

        for a in existing:
            self.staff_workload[a.staff_id] += 1
            if 'nuit' in a.shift.shift_type.name.lower():
                self.staff_nights[a.staff_id].append(a.shift.start_datetime.date())
            if a.shift.start_datetime.weekday() >= 5:
                self.staff_weekends[a.staff_id] += 1
            self.staff_services[a.staff_id].add(a.shift.care_unit.service_id)

        # Charger les règles
        self.max_consecutive_nights = self._get_rule('max_consecutive_nights', 3)
        self.max_weekend_per_month = self._get_rule('max_weekend_per_month', 2)

    def _get_rule(self, rule_type, default):
        """Récupère une règle depuis la base"""
        rule = Rule.objects.filter(rule_type=rule_type).first()
        return float(rule.value) if rule else default

    def _find_best_candidate(self, shift):
        """
        Heuristique gloutonne :
        Parmi les soignants éligibles (contraintes dures OK),
        choisir celui avec le score de pénalité le plus bas
        """
        eligible = []
        
        for staff in Staff.objects.filter(is_active=True):
            # Vérifier contraintes dures
            violations = validate_assignment(staff.id, shift.id)
            if not violations:
                eligible.append(staff)

        if not eligible:
            return None

        # Scorer chaque candidat
        best_staff = None
        best_score = float('inf')

        for staff in eligible:
            score = self._calculate_soft_score(staff, shift)
            if score < best_score:
                best_score = score
                best_staff = staff

        if best_staff:
            self.total_soft_score += best_score

        return best_staff

    def _calculate_soft_score(self, staff, shift):
        """
        Calcule le score total de pénalités pour un soignant.
        Plus le score est bas, meilleur est le candidat.
        """
        score = 0.0

        # 1. Nuits consécutives
        p1 = self._penalty_consecutive_nights(staff, shift)
        score += p1 * self.WEIGHTS['consecutive_nights']
        self.penalties_detail['consecutive_nights'] += p1

        # 2. Préférences
        p2 = self._penalty_preferences(staff, shift)
        score += p2 * self.WEIGHTS['preferences']
        self.penalties_detail['preferences'] += p2

        # 3. Équilibre de charge
        p3 = self._penalty_workload(staff)
        score += p3 * self.WEIGHTS['workload_balance']
        self.penalties_detail['workload_balance'] += p3

        # 4. Changement de service
        p4 = self._penalty_service_change(staff, shift)
        score += p4 * self.WEIGHTS['service_change']
        self.penalties_detail['service_change'] += p4

        # 5. Week-end
        p5 = self._penalty_weekend(staff, shift)
        score += p5 * self.WEIGHTS['weekend']
        self.penalties_detail['weekend'] += p5

        return score

    def _penalty_consecutive_nights(self, staff, shift):
        """
        Pénalité si trop de nuits consécutives.
        Vérifie les nuits dans les N derniers jours.
        """
        if 'nuit' not in shift.shift_type.name.lower():
            return 0

        shift_date = shift.start_datetime.date()
        recent_nights = [
            d for d in self.staff_nights.get(staff.id, [])
            if 0 <= (shift_date - d).days <= self.max_consecutive_nights
        ]

        consecutive = len(recent_nights)
        if consecutive >= self.max_consecutive_nights:
            return 50  # Forte pénalité
        elif consecutive >= self.max_consecutive_nights - 1:
            return 20  # Pénalité moyenne
        return 0

    def _penalty_preferences(self, staff, shift):
        """
        Pénalité si on viole les préférences du soignant.
        Contrainte dure = pénalité maximale
        Préférence souple = pénalité légère
        """
        shift_date = shift.start_datetime.date()
        day_of_week = shift_date.weekday()
        penalty = 0

        preferences = Preference.objects.filter(
            staff=staff,
            start_date__lte=shift_date
        ).filter(
            Q(end_date__gte=shift_date) | Q(end_date__isnull=True)
        )

        for pref in preferences:
            violated = False

            if pref.day_of_week is not None and pref.day_of_week == day_of_week:
                violated = True
            if pref.shift_type_id and pref.shift_type_id == shift.shift_type_id:
                violated = True

            if violated:
                if pref.is_hard_constraint:
                    penalty += 100  # Ne devrait jamais arriver (bloqué par les dures)
                else:
                    penalty += 15   # Préférence souple non respectée

        return penalty

    def _penalty_workload(self, staff):
        """
        Pénalité basée sur le déséquilibre de charge.
        Favorise le soignant le moins chargé.
        """
        current_load = self.staff_workload.get(staff.id, 0)

        if not self.staff_workload:
            return 0

        avg_load = sum(self.staff_workload.values()) / max(len(self.staff_workload), 1)
        diff = current_load - avg_load

        if diff > 3:
            return 30  # Très surchargé
        elif diff > 1:
            return 10  # Un peu surchargé
        elif diff < -1:
            return -5  # Bonus : sous-chargé (on le favorise)
        return 0

    def _penalty_service_change(self, staff, shift):
        """
        Pénalité si le soignant change de service dans la semaine.
        """
        current_service = shift.care_unit.service_id
        staff_assigned_services = self.staff_services.get(staff.id, set())

        if staff_assigned_services and current_service not in staff_assigned_services:
            return 20  # Changement de service
        return 0

    def _penalty_weekend(self, staff, shift):
        """
        Pénalité pour les week-ends.
        Favorise l'équité des week-ends travaillés.
        """
        day = shift.start_datetime.weekday()
        if day < 5:  # Pas un week-end
            return 0

        current_weekends = self.staff_weekends.get(staff.id, 0)
        if current_weekends >= self.max_weekend_per_month:
            return 40  # Trop de week-ends
        elif current_weekends >= self.max_weekend_per_month - 1:
            return 15
        return 0

    def _update_context(self, staff, shift):
        """Met à jour le contexte après une affectation"""
        self.staff_workload[staff.id] += 1
        
        if 'nuit' in shift.shift_type.name.lower():
            self.staff_nights[staff.id].append(shift.start_datetime.date())
        
        if shift.start_datetime.weekday() >= 5:
            self.staff_weekends[staff.id] += 1
        
        self.staff_services[staff.id].add(shift.care_unit.service_id)

    def _build_result(self, total_shifts):
        """Construit le résultat final"""
        quality = max(0, 100 - (self.total_soft_score / max(total_shifts, 1)))

        return {
            "success": self.uncovered_shifts == 0,
            "assignments_count": len(self.assignments_created),
            "total_shifts": total_shifts,
            "uncovered_shifts": self.uncovered_shifts,
            "soft_score": round(self.total_soft_score, 2),
            "quality_score": round(quality, 1),
            "penalties_detail": dict(self.penalties_detail),
            "message": self._get_message()
        }

    def _get_message(self):
        if self.uncovered_shifts == 0:
            return "Planning généré avec succès. Toutes les gardes sont couvertes."
        elif len(self.assignments_created) > 0:
            return f"Planning partiel. {self.uncovered_shifts} garde(s) non couverte(s) par manque de personnel éligible."
        return "Impossible de générer le planning. Aucune garde n'a pu être couverte."