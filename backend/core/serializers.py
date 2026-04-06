from rest_framework import serializers
from .models import (
    Staff, Role, StaffRole, Specialty, Certification,
    StaffCertification, ContractType, Contract,
    AbsenceType, Absence, Preference,
    Service, CareUnit, ServiceStatus,
    StaffServiceAssignment, PatientLoad, StaffLoan,
    ShiftType, Shift, ShiftRequiredCertification,
    ShiftAssignment, Rule,
)


# ─── Staff & Compétences ───

class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = '__all__'


class SpecialtySerializer(serializers.ModelSerializer):
    parent_name = serializers.CharField(source='parent.name', read_only=True, default=None)

    class Meta:
        model = Specialty
        fields = ['id', 'name', 'parent', 'parent_name']


class CertificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Certification
        fields = '__all__'


class StaffCertificationSerializer(serializers.ModelSerializer):
    certification_name = serializers.CharField(
        source='certification.name', read_only=True
    )
    is_expired = serializers.SerializerMethodField()

    class Meta:
        model = StaffCertification
        fields = [
            'id', 'staff', 'certification', 'certification_name',
            'obtained_date', 'expiration_date', 'is_expired',
        ]

    def get_is_expired(self, obj):
        if obj.expiration_date is None:
            return False
        from django.utils import timezone
        return obj.expiration_date < timezone.now().date()


class StaffListSerializer(serializers.ModelSerializer):
    """Serializer léger pour les listes."""
    roles = serializers.SerializerMethodField()

    class Meta:
        model = Staff
        fields = ['id', 'first_name', 'last_name', 'email', 'phone', 'is_active', 'roles']

    def get_roles(self, obj):
        return list(
            obj.staff_roles.values_list('role__name', flat=True)
        )


class StaffDetailSerializer(serializers.ModelSerializer):
    """Serializer complet pour le détail."""
    roles = serializers.SerializerMethodField()
    certifications = StaffCertificationSerializer(many=True, read_only=True)
    active_contract = serializers.SerializerMethodField()

    class Meta:
        model = Staff
        fields = [
            'id', 'first_name', 'last_name', 'email', 'phone',
            'is_active', 'created_at', 'roles', 'certifications',
            'active_contract',
        ]

    def get_roles(self, obj):
        return list(
            obj.staff_roles.values_list('role__name', flat=True)
        )

    def get_active_contract(self, obj):
        from django.utils import timezone
        from django.db.models import Q
        today = timezone.now().date()
        contract = obj.contracts.filter(
            start_date__lte=today
        ).filter(
            Q(end_date__gte=today) | Q(end_date__isnull=True)
        ).select_related('contract_type').first()
        if contract:
            return {
                'id': contract.id,
                'type': contract.contract_type.name,
                'start_date': str(contract.start_date),
                'end_date': str(contract.end_date) if contract.end_date else None,
                'workload_percent': contract.workload_percent,
            }
        return None


class StaffCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer pour création/modification."""
    role_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False,
    )

    class Meta:
        model = Staff
        fields = [
            'id', 'first_name', 'last_name', 'email',
            'phone', 'is_active', 'role_ids',
        ]

    def create(self, validated_data):
        role_ids = validated_data.pop('role_ids', [])
        staff = Staff.objects.create(**validated_data)
        for role_id in role_ids:
            StaffRole.objects.create(staff=staff, role_id=role_id)
        return staff

    def update(self, instance, validated_data):
        role_ids = validated_data.pop('role_ids', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if role_ids is not None:
            instance.staff_roles.all().delete()
            for role_id in role_ids:
                StaffRole.objects.create(staff=instance, role_id=role_id)
        return instance


# ─── Contrats ───

class ContractTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContractType
        fields = '__all__'


class ContractSerializer(serializers.ModelSerializer):
    contract_type_name = serializers.CharField(
        source='contract_type.name', read_only=True
    )
    staff_name = serializers.CharField(source='staff.__str__', read_only=True)

    class Meta:
        model = Contract
        fields = [
            'id', 'staff', 'staff_name', 'contract_type',
            'contract_type_name', 'start_date', 'end_date',
            'workload_percent',
        ]


# ─── Absences ───

class AbsenceTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = AbsenceType
        fields = '__all__'


class AbsenceSerializer(serializers.ModelSerializer):
    absence_type_name = serializers.CharField(
        source='absence_type.name', read_only=True
    )
    staff_name = serializers.CharField(source='staff.__str__', read_only=True)

    class Meta:
        model = Absence
        fields = [
            'id', 'staff', 'staff_name', 'absence_type',
            'absence_type_name', 'start_date', 'expected_end_date',
            'actual_end_date', 'is_planned',
        ]


# ─── Préférences ───

class PreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Preference
        fields = '__all__'


# ─── Structure ───

class ServiceSerializer(serializers.ModelSerializer):
    manager_name = serializers.CharField(
        source='manager.__str__', read_only=True, default=None
    )
    care_units_count = serializers.SerializerMethodField()

    class Meta:
        model = Service
        fields = [
            'id', 'name', 'manager', 'manager_name',
            'bed_capacity', 'criticality_level', 'care_units_count',
        ]

    def get_care_units_count(self, obj):
        return obj.care_units.count()


class CareUnitSerializer(serializers.ModelSerializer):
    service_name = serializers.CharField(source='service.name', read_only=True)

    class Meta:
        model = CareUnit
        fields = ['id', 'service', 'service_name', 'name']


# ─── Planning ───

class ShiftTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShiftType
        fields = '__all__'


class ShiftSerializer(serializers.ModelSerializer):
    care_unit_name = serializers.CharField(source='care_unit.__str__', read_only=True)
    shift_type_name = serializers.CharField(source='shift_type.name', read_only=True)
    shift_type_duration = serializers.IntegerField(
        source='shift_type.duration_hours', read_only=True
    )
    current_staff_count = serializers.SerializerMethodField()
    required_certifications = serializers.SerializerMethodField()

    class Meta:
        model = Shift
        fields = [
            'id', 'care_unit', 'care_unit_name', 'shift_type',
            'shift_type_name', 'shift_type_duration',
            'start_datetime', 'end_datetime',
            'min_staff', 'max_staff', 'current_staff_count',
            'required_certifications',
        ]

    def get_current_staff_count(self, obj):
        return obj.assignments.count()

    def get_required_certifications(self, obj):
        return list(
            obj.required_certifications.values_list(
                'certification__name', flat=True
            )
        )


class ShiftAssignmentSerializer(serializers.ModelSerializer):
    staff_name = serializers.CharField(source='staff.__str__', read_only=True)
    shift_info = serializers.SerializerMethodField()

    class Meta:
        model = ShiftAssignment
        fields = [
            'id', 'shift', 'staff', 'staff_name',
            'assigned_at', 'shift_info',
        ]

    def get_shift_info(self, obj):
        return {
            'shift_type': obj.shift.shift_type.name,
            'care_unit': str(obj.shift.care_unit),
            'start': str(obj.shift.start_datetime),
            'end': str(obj.shift.end_datetime),
        }


class ShiftAssignmentCreateSerializer(serializers.Serializer):
    """
    Serializer spécial pour la CRÉATION d'affectation.
    Intègre la validation des contraintes dures.
    """
    staff_id = serializers.IntegerField()
    shift_id = serializers.IntegerField()

    def validate(self, data):
        from .validators import validate_assignment

        violations = validate_assignment(data['staff_id'], data['shift_id'])

        if violations:
            error_details = {
                'message': 'Affectation refusée — contraintes dures violées.',
                'violations': [v.to_dict() for v in violations],
                'violations_count': len(violations),
            }
            raise serializers.ValidationError(error_details)

        return data

    def create(self, validated_data):
        return ShiftAssignment.objects.create(
            staff_id=validated_data['staff_id'],
            shift_id=validated_data['shift_id'],
        )


# ─── Prêts ───

class StaffLoanSerializer(serializers.ModelSerializer):
    staff_name = serializers.CharField(source='staff.__str__', read_only=True)
    from_service_name = serializers.CharField(source='from_service.name', read_only=True)
    to_service_name = serializers.CharField(source='to_service.name', read_only=True)

    class Meta:
        model = StaffLoan
        fields = [
            'id', 'staff', 'staff_name',
            'from_service', 'from_service_name',
            'to_service', 'to_service_name',
            'start_date', 'end_date',
        ]


# ─── Charge patiente ───

class PatientLoadSerializer(serializers.ModelSerializer):
    care_unit_name = serializers.CharField(source='care_unit.__str__', read_only=True)

    class Meta:
        model = PatientLoad
        fields = [
            'id', 'care_unit', 'care_unit_name',
            'date', 'patient_count', 'occupancy_rate',
        ]


# ─── Règles ───

class RuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rule
        fields = '__all__'