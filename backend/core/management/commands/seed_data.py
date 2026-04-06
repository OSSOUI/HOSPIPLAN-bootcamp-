from django.core.management.base import BaseCommand
from datetime import date, timedelta, datetime
from django.utils import timezone
import random

from core.models import *


class Command(BaseCommand):
    help = "Peuplement complet et réaliste de la base pour tester les affectations"

    def handle(self, *args, **options):
        self.stdout.write("🌱 Peuplement de la base HospiPlan en cours...")

        # ====================== DONNÉES DE RÉFÉRENCE ======================
        roles = {name: Role.objects.get_or_create(name=name)[0] for name in 
                ['Médecin', 'Infirmier(ère)', 'Aide-soignant(e)']}

        specialties = {}
        for name in ['Urgences', 'Cardiologie', 'Pédiatrie', 'Réanimation']:
            specialties[name] = Specialty.objects.get_or_create(name=name)[0]

        certs = {}
        for name in ['AFGSU Niveau 1', 'AFGSU Niveau 2', 'Réanimation Cardio-Pulmonaire']:
            certs[name] = Certification.objects.get_or_create(name=name)[0]

        # ====================== TYPES DE CONTRATS & ABSENCES ======================
        ct_cdi = ContractType.objects.get_or_create(
            name='CDI', defaults={'max_hours_per_week': 48, 'night_shift_allowed': True})[0]
        ct_cdd = ContractType.objects.get_or_create(
            name='CDD', defaults={'max_hours_per_week': 44, 'night_shift_allowed': True})[0]

        absence_type = AbsenceType.objects.get_or_create(name='Congés annuels', impacts_quota=True)[0]

        # ====================== RÈGLES MÉTIER ======================
        Rule.objects.get_or_create(rule_type='max_weekly_hours', defaults={
            'name': 'Heures max par semaine', 'value': 48, 'unit': 'heures', 'valid_from': date(2024,1,1)})
        Rule.objects.get_or_create(rule_type='min_rest_hours', defaults={
            'name': 'Repos minimum', 'value': 11, 'unit': 'heures', 'valid_from': date(2024,1,1)})

        # ====================== SOIGNANTS (8 personnes) ======================
        staff_list = []
        data = [
            ("Amine", "Benali", "amine.benali@alamal.ma", "Médecin"),
            ("Fatima", "El Amrani", "fatima.elamrani@alamal.ma", "Infirmier(ère)"),
            ("Youssef", "Tazi", "youssef.tazi@alamal.ma", "Infirmier(ère)"),
            ("Khadija", "Idrissi", "khadija.idrissi@alamal.ma", "Infirmier(ère)"),
            ("Omar", "Cherkaoui", "omar.cherkaoui@alamal.ma", "Médecin"),
            ("Salma", "Berrada", "salma.berrada@alamal.ma", "Aide-soignant(e)"),
        ]

        for first, last, email, role_name in data:
            staff = Staff.objects.get_or_create(
                email=email,
                defaults={'first_name': first, 'last_name': last, 'is_active': True}
            )[0]
            staff_list.append(staff)

            # Rôle
            StaffRole.objects.get_or_create(staff=staff, role=roles[role_name])
            
            # Certification
            StaffCertification.objects.get_or_create(
                staff=staff,
                certification=certs['AFGSU Niveau 2'],
                defaults={'obtained_date': date(2023,1,1), 'expiration_date': date(2026,12,31)}
            )

        self.stdout.write(f"✓ {len(staff_list)} soignants créés")

        # ====================== SERVICES & UNITÉS ======================
        urgences = Service.objects.get_or_create(name="Urgences", defaults={
            'bed_capacity': 40, 'criticality_level': 5})[0]
        cardio = Service.objects.get_or_create(name="Cardiologie", defaults={
            'bed_capacity': 30, 'criticality_level': 4})[0]

        CareUnit.objects.get_or_create(service=urgences, name="Urgences Adultes")
        CareUnit.objects.get_or_create(service=urgences, name="Urgences Pédiatriques")
        CareUnit.objects.get_or_create(service=cardio, name="Cardiologie")

        # ====================== TYPES DE GARDES ======================
        shift_types = {}
        for name, hours in [('Matin', 8), ('Après-midi', 8), ('Nuit', 12)]:
            shift_types[name] = ShiftType.objects.get_or_create(
                name=name, defaults={'duration_hours': hours, 'requires_rest_after': True}
            )[0]

        # ====================== CRÉATION DE SHIFTS (7 jours) ======================
        care_unit = CareUnit.objects.first()
        shifts_created = 0
        today = date.today()

        for i in range(7):  # 7 prochains jours
            day = today + timedelta(days=i)
            for st_name in ['Matin', 'Après-midi', 'Nuit']:
                start_hour = 7 if st_name == 'Matin' else 14 if st_name == 'Après-midi' else 21
                start = timezone.make_aware(datetime.combine(day, datetime.min.time().replace(hour=start_hour)))
                end = start + timedelta(hours=shift_types[st_name].duration_hours)

                shift = Shift.objects.get_or_create(
                    care_unit=care_unit,
                    shift_type=shift_types[st_name],
                    start_datetime=start,
                    defaults={'end_datetime': end, 'min_staff': 2, 'max_staff': 4}
                )[0]
                shifts_created += 1

        self.stdout.write(f"✓ {shifts_created} créneaux de garde créés")

        # ====================== ABSENCES ======================
        Absence.objects.get_or_create(
            staff=staff_list[1],
            absence_type=absence_type,
            start_date=today + timedelta(days=2),
            expected_end_date=today + timedelta(days=5),
            defaults={'is_planned': True}
        )

        # ====================== PREFERENCES ======================
        Preference.objects.get_or_create(
            staff=staff_list[0],
            type='day_off',
            description="Refuse de travailler le vendredi",
            is_hard_constraint=True,
            start_date=today,
            day_of_week=4
        )

        self.stdout.write(self.style.SUCCESS("\n🎉 Peuplement terminé avec succès !"))
        self.stdout.write("Vous pouvez maintenant créer des affectations et tester les absences.")