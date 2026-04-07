from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()

# Staff & Compétences
router.register(r'staff', views.StaffViewSet)
router.register(r'roles', views.RoleViewSet)
router.register(r'specialties', views.SpecialtyViewSet)
router.register(r'certifications', views.CertificationViewSet)

# Contrats & Absences
router.register(r'contract-types', views.ContractTypeViewSet)
router.register(r'contracts', views.ContractViewSet)
router.register(r'absence-types', views.AbsenceTypeViewSet)
router.register(r'absences', views.AbsenceViewSet)
router.register(r'preferences', views.PreferenceViewSet)

# Structure
router.register(r'services', views.ServiceViewSet)
router.register(r'care-units', views.CareUnitViewSet)

# Planning
router.register(r'shift-types', views.ShiftTypeViewSet)
router.register(r'shifts', views.ShiftViewSet)
router.register(r'assignments', views.ShiftAssignmentViewSet)

# Prêts & Charge
router.register(r'staff-loans', views.StaffLoanViewSet)
router.register(r'patient-loads', views.PatientLoadViewSet)

# Règles
router.register(r'rules', views.RuleViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('dashboard/', views.dashboard, name='dashboard'),
]

path('plannings/generate/', views.generate_planning, name='generate-planning'),