from django.shortcuts import render
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from django.db.models import Q, Count
from django.utils import timezone

from .models import (
    Staff, Role, Specialty, Certification, StaffCertification,
    ContractType, Contract, AbsenceType, Absence, Preference,
    Service, CareUnit, StaffServiceAssignment, PatientLoad, StaffLoan,
    ShiftType, Shift, ShiftAssignment, Rule,
)
from .serializers import (
    StaffListSerializer, StaffDetailSerializer, StaffCreateUpdateSerializer,
    RoleSerializer, SpecialtySerializer,
    CertificationSerializer, StaffCertificationSerializer,
    ContractTypeSerializer, ContractSerializer,
    AbsenceTypeSerializer, AbsenceSerializer,
    PreferenceSerializer,
    ServiceSerializer, CareUnitSerializer,
    ShiftTypeSerializer, ShiftSerializer,
    ShiftAssignmentSerializer, ShiftAssignmentCreateSerializer,
    StaffLoanSerializer, PatientLoadSerializer, RuleSerializer,
)


# ═══════════════════════════════════════════════
# VUES STAFF
# ═══════════════════════════════════════════════

class StaffViewSet(viewsets.ModelViewSet):
    """
    CRUD complet pour les soignants.
    GET /api/staff/ → liste
    POST /api/staff/ → créer
    GET /api/staff/{id}/ → détail
    PUT /api/staff/{id}/ → modifier
    DELETE /api/staff/{id}/ → supprimer
    """
    queryset = Staff.objects.all()
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['first_name', 'last_name', 'email']
    ordering_fields = ['last_name', 'first_name', 'created_at']

    def get_serializer_class(self):
        if self.action == 'list':
            return StaffListSerializer
        if self.action == 'retrieve':
            return StaffDetailSerializer
        return StaffCreateUpdateSerializer

    def destroy(self, request, *args, **kwargs):
        """Soft delete — on désactive au lieu de supprimer."""
        staff = self.get_object()
        # Vérifier les affectations futures
        future_assignments = ShiftAssignment.objects.filter(
            staff=staff,
            shift__start_datetime__gte=timezone.now(),
        ).count()
        if future_assignments > 0:
            return Response(
                {
                    'error': (
                        f"Impossible de désactiver {staff} : "
                        f"{future_assignments} affectation(s) future(s) existante(s). "
                        f"Veuillez les supprimer d'abord."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )
        staff.is_active = False
        staff.save()
        return Response(
            {'message': f"{staff} a été désactivé(e)."},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=['get'])
    def absences(self, request, pk=None):
        """GET /api/staff/{id}/absences/ — absences d'un soignant."""
        staff = self.get_object()
        absences = Absence.objects.filter(staff=staff).select_related('absence_type')
        serializer = AbsenceSerializer(absences, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def assignments(self, request, pk=None):
        """GET /api/staff/{id}/assignments/ — affectations d'un soignant."""
        staff = self.get_object()
        assignments = ShiftAssignment.objects.filter(
            staff=staff
        ).select_related(
            'shift', 'shift__shift_type', 'shift__care_unit'
        ).order_by('-shift__start_datetime')
        serializer = ShiftAssignmentSerializer(assignments, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def certifications(self, request, pk=None):
        """GET /api/staff/{id}/certifications/ — certifications."""
        staff = self.get_object()
        certs = StaffCertification.objects.filter(
            staff=staff
        ).select_related('certification')
        serializer = StaffCertificationSerializer(certs, many=True)
        return Response(serializer.data)


# ═══════════════════════════════════════════════
# VUES RÉFÉRENTIELS
# ═══════════════════════════════════════════════

class RoleViewSet(viewsets.ModelViewSet):
    queryset = Role.objects.all()
    serializer_class = RoleSerializer


class SpecialtyViewSet(viewsets.ModelViewSet):
    queryset = Specialty.objects.select_related('parent').all()
    serializer_class = SpecialtySerializer


class CertificationViewSet(viewsets.ModelViewSet):
    queryset = Certification.objects.all()
    serializer_class = CertificationSerializer


class ContractTypeViewSet(viewsets.ModelViewSet):
    queryset = ContractType.objects.all()
    serializer_class = ContractTypeSerializer


class AbsenceTypeViewSet(viewsets.ModelViewSet):
    queryset = AbsenceType.objects.all()
    serializer_class = AbsenceTypeSerializer


class RuleViewSet(viewsets.ModelViewSet):
    queryset = Rule.objects.all()
    serializer_class = RuleSerializer


# ═══════════════════════════════════════════════
# VUES CONTRATS & ABSENCES
# ═══════════════════════════════════════════════

class ContractViewSet(viewsets.ModelViewSet):
    queryset = Contract.objects.select_related('staff', 'contract_type').all()
    serializer_class = ContractSerializer


class AbsenceViewSet(viewsets.ModelViewSet):
    queryset = Absence.objects.select_related('staff', 'absence_type').all()
    serializer_class = AbsenceSerializer
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['start_date']

    def get_queryset(self):
        qs = super().get_queryset()
        staff_id = self.request.query_params.get('staff_id')
        if staff_id:
            qs = qs.filter(staff_id=staff_id)
        return qs


class PreferenceViewSet(viewsets.ModelViewSet):
    queryset = Preference.objects.select_related('staff').all()
    serializer_class = PreferenceSerializer


# ═══════════════════════════════════════════════
# VUES STRUCTURE
# ═══════════════════════════════════════════════

class ServiceViewSet(viewsets.ModelViewSet):
    queryset = Service.objects.select_related('manager').all()
    serializer_class = ServiceSerializer


class CareUnitViewSet(viewsets.ModelViewSet):
    queryset = CareUnit.objects.select_related('service').all()
    serializer_class = CareUnitSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        service_id = self.request.query_params.get('service_id')
        if service_id:
            qs = qs.filter(service_id=service_id)
        return qs


# ═══════════════════════════════════════════════
# VUES PLANNING — LE CŒUR
# ═══════════════════════════════════════════════

class ShiftTypeViewSet(viewsets.ModelViewSet):
    queryset = ShiftType.objects.all()
    serializer_class = ShiftTypeSerializer


class ShiftViewSet(viewsets.ModelViewSet):
    """
    CRUD pour les créneaux de garde.
    Filtrage par care_unit, date, et sous-couverture.
    """
    queryset = Shift.objects.select_related(
        'care_unit', 'care_unit__service', 'shift_type'
    ).all()
    serializer_class = ShiftSerializer
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['start_datetime']

    def get_queryset(self):
        qs = super().get_queryset()

        # Filtre par unité de soins
        care_unit_id = self.request.query_params.get('care_unit_id')
        if care_unit_id:
            qs = qs.filter(care_unit_id=care_unit_id)

        # Filtre par service
        service_id = self.request.query_params.get('service_id')
        if service_id:
            qs = qs.filter(care_unit__service_id=service_id)

        # Filtre par plage de dates
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        if date_from:
            qs = qs.filter(start_datetime__date__gte=date_from)
        if date_to:
            qs = qs.filter(start_datetime__date__lte=date_to)

        # Filtre : gardes sous-couvertes uniquement
        understaffed = self.request.query_params.get('understaffed')
        if understaffed == 'true':
            qs = qs.annotate(
                assignment_count=Count('assignments')
            ).filter(
                assignment_count__lt=models.F('min_staff')
            )

        return qs

    @action(detail=True, methods=['get'])
    def assignments(self, request, pk=None):
        """GET /api/shifts/{id}/assignments/ — qui est affecté à cette garde."""
        shift = self.get_object()
        assignments = ShiftAssignment.objects.filter(
            shift=shift
        ).select_related('staff')
        serializer = ShiftAssignmentSerializer(assignments, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def eligible_staff(self, request, pk=None):
        """
        GET /api/shifts/{id}/eligible_staff/
        Liste les soignants éligibles pour cette garde
        (disponibles, certifiés, contrat valide).
        """
        shift = self.get_object()
        from .validators import validate_assignment

        # Récupérer tous les soignants actifs
        all_staff = Staff.objects.filter(is_active=True)
        eligible = []
        ineligible = []

        for s in all_staff:
            violations = validate_assignment(s.id, shift.id)
            if not violations:
                eligible.append({
                    'id': s.id,
                    'name': str(s),
                    'eligible': True,
                })
            else:
                ineligible.append({
                    'id': s.id,
                    'name': str(s),
                    'eligible': False,
                    'reasons': [v.message for v in violations],
                })

        return Response({
            'shift_id': shift.id,
            'eligible': eligible,
            'ineligible': ineligible,
            'eligible_count': len(eligible),
            'total_checked': len(all_staff),
        })


class ShiftAssignmentViewSet(viewsets.ModelViewSet):
    """
    Gestion des affectations.
    La CRÉATION passe par le validateur de contraintes dures.
    """
    queryset = ShiftAssignment.objects.select_related(
        'staff', 'shift', 'shift__shift_type', 'shift__care_unit'
    ).all()

    def get_serializer_class(self):
        if self.action == 'create':
            return ShiftAssignmentCreateSerializer
        return ShiftAssignmentSerializer

    def create(self, request, *args, **kwargs):
        """
        POST /api/assignments/
        Body : {"staff_id": 1, "shift_id": 5}

        Les contraintes dures sont validées dans le serializer.
        Si une violation est détectée, l'API retourne 400 avec le détail.
        """
        serializer = ShiftAssignmentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        assignment = serializer.save()

        # Retourner l'affectation créée avec le serializer de lecture
        output = ShiftAssignmentSerializer(assignment)
        return Response(output.data, status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        assignment = self.get_object()
        assignment.delete()
        return Response(
            {'message': 'Affectation supprimée.'},
            status=status.HTTP_200_OK,
        )


# ═══════════════════════════════════════════════
# VUES PRÊTS & CHARGE PATIENTE
# ═══════════════════════════════════════════════

class StaffLoanViewSet(viewsets.ModelViewSet):
    queryset = StaffLoan.objects.select_related(
        'staff', 'from_service', 'to_service'
    ).all()
    serializer_class = StaffLoanSerializer


class PatientLoadViewSet(viewsets.ModelViewSet):
    queryset = PatientLoad.objects.select_related('care_unit').all()
    serializer_class = PatientLoadSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        care_unit_id = self.request.query_params.get('care_unit_id')
        if care_unit_id:
            qs = qs.filter(care_unit_id=care_unit_id)
        return qs


# ═══════════════════════════════════════════════
# VUE DASHBOARD — résumé global
# ═══════════════════════════════════════════════

@api_view(['GET'])
def dashboard(request):
    """
    GET /api/dashboard/
    Vue de synthèse pour le frontend.
    """
    today = timezone.now().date()
    now = timezone.now()

    # Compteurs globaux
    total_staff = Staff.objects.filter(is_active=True).count()
    total_services = Service.objects.count()

    # Absences aujourd'hui
    absences_today = Absence.objects.filter(
        start_date__lte=today,
    ).filter(
        Q(actual_end_date__gte=today) |
        (Q(actual_end_date__isnull=True) & Q(expected_end_date__gte=today))
    ).count()

    # Gardes aujourd'hui
    shifts_today = Shift.objects.filter(
        start_datetime__date=today
    ).count()

    # Gardes non couvertes (sous min_staff) aujourd'hui
    understaffed_today = 0
    for shift in Shift.objects.filter(start_datetime__date=today):
        if shift.assignments.count() < shift.min_staff:
            understaffed_today += 1

    # Certifications expirant dans 30 jours
    expiring_certs = StaffCertification.objects.filter(
        expiration_date__gte=today,
        expiration_date__lte=today + timezone.timedelta(days=30),
    ).count()

    return Response({
        'date': str(today),
        'total_active_staff': total_staff,
        'total_services': total_services,
        'absences_today': absences_today,
        'shifts_today': shifts_today,
        'understaffed_shifts_today': understaffed_today,
        'certifications_expiring_30d': expiring_certs,
    })