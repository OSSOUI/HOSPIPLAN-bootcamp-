from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


# ============================================================
# BLOC 1 : Personnel & Compétences (F-01, F-03)
# ============================================================

class Staff(models.Model):
    """Table maîtresse — identité physique de chaque soignant."""
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'staff'
        ordering = ['last_name', 'first_name']

    def __str__(self):
        return f"{self.last_name} {self.first_name}"


class Role(models.Model):
    """Table de référence des métiers (Médecin, IDE, AS...)."""
    name = models.CharField(max_length=100)

    class Meta:
        db_table = 'role'

    def __str__(self):
        return self.name


class StaffRole(models.Model):
    """Liaison N:N entre staff et role."""
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name='staff_roles')
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name='role_staff')

    class Meta:
        db_table = 'staff_role'
        unique_together = ('staff', 'role')

    def __str__(self):
        return f"{self.staff} — {self.role}"


class Specialty(models.Model):
    """Spécialités médicales avec hiérarchie récursive."""
    name = models.CharField(max_length=100)
    parent = models.ForeignKey(
        'self', on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='sub_specialties'
    )

    class Meta:
        db_table = 'specialty'
        verbose_name_plural = 'specialties'

    def __str__(self):
        return self.name


class StaffSpecialty(models.Model):
    """Liaison N:N entre staff et specialty."""
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name='staff_specialties')
    specialty = models.ForeignKey(Specialty, on_delete=models.CASCADE, related_name='specialty_staff')

    class Meta:
        db_table = 'staff_specialty'
        unique_together = ('staff', 'specialty')


class Certification(models.Model):
    """Catalogue des certifications techniques."""
    name = models.CharField(max_length=150)

    class Meta:
        db_table = 'certification'

    def __str__(self):
        return self.name


class CertificationDependency(models.Model):
    """Prérequis entre certifications (récursif)."""
    parent_cert = models.ForeignKey(
        Certification, on_delete=models.CASCADE,
        related_name='dependencies'
    )
    required_cert = models.ForeignKey(
        Certification, on_delete=models.CASCADE,
        related_name='required_by'
    )

    class Meta:
        db_table = 'certification_dependency'
        unique_together = ('parent_cert', 'required_cert')


class StaffCertification(models.Model):
    """Historique individuel des certifications obtenues."""
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name='certifications')
    certification = models.ForeignKey(Certification, on_delete=models.CASCADE)
    obtained_date = models.DateField()
    expiration_date = models.DateField(null=True, blank=True)

    class Meta:
        db_table = 'staff_certification'

    def __str__(self):
        return f"{self.staff} — {self.certification}"


# ============================================================
# BLOC 2 : Contractuel & Social (F-02, F-06, F-07)
# ============================================================

class ContractType(models.Model):
    """Types de contrats avec règles par défaut."""
    name = models.CharField(max_length=50)
    max_hours_per_week = models.IntegerField(null=True, blank=True)
    leave_days_per_year = models.IntegerField(null=True, blank=True)
    night_shift_allowed = models.BooleanField(default=True)

    class Meta:
        db_table = 'contract_type'

    def __str__(self):
        return self.name


class Contract(models.Model):
    """Instance réelle d'un contrat pour un agent."""
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name='contracts')
    contract_type = models.ForeignKey(ContractType, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    workload_percent = models.IntegerField(
        default=100,
        validators=[MinValueValidator(1), MaxValueValidator(100)]
    )

    class Meta:
        db_table = 'contract'
        ordering = ['-start_date']

    def __str__(self):
        status = "actif" if self.end_date is None else f"fin {self.end_date}"
        return f"{self.staff} — {self.contract_type} ({status})"


class AbsenceType(models.Model):
    """Dictionnaire des motifs d'absence."""
    name = models.CharField(max_length=50)
    impacts_quota = models.BooleanField(default=True)

    class Meta:
        db_table = 'absence_type'

    def __str__(self):
        return self.name


class Absence(models.Model):
    """Périodes d'indisponibilité enregistrées."""
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name='absences')
    absence_type = models.ForeignKey(AbsenceType, on_delete=models.CASCADE)
    start_date = models.DateField()
    expected_end_date = models.DateField()
    actual_end_date = models.DateField(null=True, blank=True)
    is_planned = models.BooleanField(default=True)

    class Meta:
        db_table = 'absence'
        ordering = ['-start_date']

    def __str__(self):
        return f"{self.staff} — {self.absence_type} ({self.start_date})"


class Preference(models.Model):
    """Souhaits ou interdits déclarés par les agents."""
    PREFERENCE_TYPES = [
        ('shift_preference', 'Préférence de créneau'),
        ('day_off', 'Jour non travaillé'),
        ('other', 'Autre'),
    ]

    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name='preferences')
    type = models.CharField(max_length=50, choices=PREFERENCE_TYPES)
    description = models.TextField(blank=True)
    is_hard_constraint = models.BooleanField(default=False)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    # Champs optionnels pour filtrage précis
    day_of_week = models.IntegerField(
        null=True, blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(6)],
        help_text="0=Lundi, 6=Dimanche"
    )
    shift_type = models.ForeignKey(
        'ShiftType', on_delete=models.SET_NULL,
        null=True, blank=True,
        help_text="Type de garde concerné par la préférence"
    )

    class Meta:
        db_table = 'preference'

    def __str__(self):
        kind = "CONTRAINTE" if self.is_hard_constraint else "Préférence"
        return f"{kind}: {self.staff} — {self.description[:50]}"


# ============================================================
# BLOC 3 : Structure & Flux (F-04, F-08, F-09)
# ============================================================

class Service(models.Model):
    """Entité administrative (Cardiologie, Urgences...)."""
    name = models.CharField(max_length=100)
    manager = models.ForeignKey(
        Staff, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='managed_services'
    )
    bed_capacity = models.IntegerField()
    criticality_level = models.IntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )

    class Meta:
        db_table = 'service'

    def __str__(self):
        return self.name


class CareUnit(models.Model):
    """Unité de soins opérationnelle au sein d'un service."""
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='care_units')
    name = models.CharField(max_length=100)

    class Meta:
        db_table = 'care_unit'

    def __str__(self):
        return f"{self.service.name} — {self.name}"


class ServiceStatus(models.Model):
    """Historique des états d'un service (ouvert, fermé, sous-effectif)."""
    STATUS_CHOICES = [
        ('open', 'Ouvert'),
        ('closed', 'Fermé'),
        ('understaffed', 'Sous-effectif'),
    ]

    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='statuses')
    status = models.CharField(max_length=50, choices=STATUS_CHOICES)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)

    class Meta:
        db_table = 'service_status'

    def __str__(self):
        return f"{self.service} — {self.status} ({self.start_date})"


class StaffServiceAssignment(models.Model):
    """Affectation d'un soignant à un service (port d'attache)."""
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name='service_assignments')
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='staff_assignments')
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)

    class Meta:
        db_table = 'staff_service_assignment'

    def __str__(self):
        return f"{self.staff} → {self.service}"


class PatientLoad(models.Model):
    """Données quotidiennes d'occupation des lits."""
    care_unit = models.ForeignKey(CareUnit, on_delete=models.CASCADE, related_name='patient_loads')
    date = models.DateField()
    patient_count = models.IntegerField(validators=[MinValueValidator(0)])
    occupancy_rate = models.FloatField(
        null=True, blank=True,
        validators=[MinValueValidator(0.0)]
    )

    class Meta:
        db_table = 'patient_load'
        unique_together = ('care_unit', 'date')

    def __str__(self):
        return f"{self.care_unit} — {self.date}: {self.patient_count} patients"


class StaffLoan(models.Model):
    """Prêt temporaire d'un soignant d'un service à un autre."""
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name='loans')
    from_service = models.ForeignKey(
        Service, on_delete=models.CASCADE, related_name='loans_out'
    )
    to_service = models.ForeignKey(
        Service, on_delete=models.CASCADE, related_name='loans_in'
    )
    start_date = models.DateField()
    end_date = models.DateField()

    class Meta:
        db_table = 'staff_loan'

    def __str__(self):
        return f"{self.staff}: {self.from_service} → {self.to_service}"


# ============================================================
# BLOC 4 : Planning & Gardes (F-05)
# ============================================================

class ShiftType(models.Model):
    """Modèle de garde (Nuit 12h, Matin 7h-14h...)."""
    name = models.CharField(max_length=50)
    duration_hours = models.IntegerField(validators=[MinValueValidator(1)])
    requires_rest_after = models.BooleanField(default=True)

    class Meta:
        db_table = 'shift_type'

    def __str__(self):
        return f"{self.name} ({self.duration_hours}h)"


class Shift(models.Model):
    """Instance concrète d'un créneau de garde dans une unité."""
    care_unit = models.ForeignKey(CareUnit, on_delete=models.CASCADE, related_name='shifts')
    shift_type = models.ForeignKey(ShiftType, on_delete=models.CASCADE, related_name='shifts')
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()
    min_staff = models.IntegerField(default=1, validators=[MinValueValidator(0)])
    max_staff = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = 'shift'
        ordering = ['start_datetime']

    def __str__(self):
        return (
            f"{self.shift_type.name} — {self.care_unit} "
            f"({self.start_datetime.strftime('%d/%m %H:%M')})"
        )


class ShiftRequiredCertification(models.Model):
    """Certifications requises pour un créneau de garde."""
    shift = models.ForeignKey(Shift, on_delete=models.CASCADE, related_name='required_certifications')
    certification = models.ForeignKey(Certification, on_delete=models.CASCADE)

    class Meta:
        db_table = 'shift_required_certification'
        unique_together = ('shift', 'certification')


class ShiftAssignment(models.Model):
    """Affectation effective d'un soignant à une garde."""
    shift = models.ForeignKey(Shift, on_delete=models.CASCADE, related_name='assignments')
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name='shift_assignments')
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'shift_assignment'
        unique_together = ('shift', 'staff')

    def __str__(self):
        return f"{self.staff} → {self.shift}"


# ============================================================
# BLOC 5 : Configuration (F-10)
# ============================================================

class Rule(models.Model):
    """Règles métier configurables (pas codées en dur)."""
    RULE_TYPES = [
        ('max_weekly_hours', 'Heures max par semaine'),
        ('min_rest_hours', 'Repos minimum entre gardes (h)'),
        ('max_consecutive_nights', 'Nuits consécutives max'),
        ('max_weekend_per_month', 'Week-ends max par mois'),
        ('overactivity_threshold', 'Seuil de sur-activité (%)'),
    ]

    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    rule_type = models.CharField(max_length=50, choices=RULE_TYPES)
    value = models.DecimalField(max_digits=10, decimal_places=2)
    unit = models.CharField(max_length=20, help_text="hours, days, percent...")
    valid_from = models.DateField()
    valid_to = models.DateField(null=True, blank=True)

    class Meta:
        db_table = 'rule'

    def __str__(self):
        return f"{self.name}: {self.value} {self.unit}"