"""
Idempotent demo data seeder for Nexus Career.
Populates accounts across all roles (Student, Recruiter, Alumni, IPC Admin, System Admin),
verified/pending companies, published/pending/draft opportunities, student profiles with PDF resumes,
applications with status history, alumni profiles with graduation proofs, referral requests,
and in-app notifications.
"""

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.alumni.models import AlumniProfile, ReferralRequest, ReferralRequestHistory
from apps.applications.models import Application, ApplicationStatusHistory
from apps.notifications.models import Notification
from apps.opportunities.eligibility import evaluate_eligibility
from apps.opportunities.models import Opportunity
from apps.recruiters.models import Company, RecruiterProfile, WorkflowAuditEvent
from apps.students.models import StudentProfile

User = get_user_model()

DEMO_PASSWORD = "NexusDemo@2026!"

MINIMAL_PDF = (
    b"%PDF-1.4\n"
    b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
    b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
    b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\n"
    b"xref\n0 4\n0000000000 65535 f \n"
    b"trailer\n<< /Root 1 0 R /Size 4 >>\nstartxref\n190\n%%EOF\n"
)


def _upsert_user(username, email, role, first_name, last_name, is_verified=True, is_staff=False, is_superuser=False):
    user, _ = User.objects.update_or_create(
        username=username,
        defaults={
            "email": email,
            "role": role,
            "first_name": first_name,
            "last_name": last_name,
            "is_verified": is_verified,
            "is_staff": is_staff,
            "is_superuser": is_superuser,
            "is_active": True,
        },
    )
    if not user.check_password(DEMO_PASSWORD):
        user.set_password(DEMO_PASSWORD)
        user.save(update_fields=["password"])
    return user


class Command(BaseCommand):
    help = "Seed idempotent demo accounts, companies, opportunities, applications, alumni, referrals, and notifications."

    @transaction.atomic
    def handle(self, *args, **options):
        now = timezone.now()

        # 1. Admin & IPC Admin Accounts
        sys_admin = _upsert_user(
            username="sys_admin",
            email="admin@scds.saiuniversity.edu.in",
            role=User.Role.SYSTEM_ADMIN,
            first_name="System",
            last_name="Administrator",
            is_verified=True,
            is_staff=True,
            is_superuser=True,
        )
        ipc_admin = _upsert_user(
            username="ipc_admin",
            email="ipc.admin@scds.saiuniversity.edu.in",
            role=User.Role.IPC_ADMIN,
            first_name="Meenakshi",
            last_name="Iyer",
            is_verified=True,
            is_staff=True,
        )

        # 2. Student Accounts & Profiles
        rahul = _upsert_user(
            username="rahul_student",
            email="rahul.n-27@scds.saiuniversity.edu.in",
            role=User.Role.STUDENT,
            first_name="Rahul",
            last_name="N",
            is_verified=True,
        )
        rahul_profile, _ = StudentProfile.objects.update_or_create(
            user=rahul,
            defaults={
                "student_id": "SCDS-2023-042",
                "department": "Computer Science",
                "degree_programme": "B.Tech",
                "graduation_year": 2027,
                "cgpa": Decimal("8.95"),
                "skills": [
                    "Python",
                    "TypeScript",
                    "React",
                    "Django",
                    "PostgreSQL",
                    "Docker",
                    "Kubernetes",
                    "SQL",
                ],
                "areas_of_interest": [
                    "Full-Stack Engineering",
                    "Cloud & DevOps",
                    "Distributed Systems",
                ],
                "experience": "Software Engineering Intern at CloudNative Labs (Summer 2026); Lead Developer for Nexus Career platform.",
                "preferred_roles": ["Software Engineer", "DevOps Engineer", "Backend Engineer"],
                "preferred_locations": ["Bengaluru", "Chennai", "Hyderabad", "Remote"],
                "work_mode": "HYBRID",
            },
        )
        if not rahul_profile.has_resume:
            rahul_profile.resume.save("rahul_resume.pdf", ContentFile(MINIMAL_PDF), save=True)

        ananya = _upsert_user(
            username="ananya_student",
            email="ananya.s-27@scds.saiuniversity.edu.in",
            role=User.Role.STUDENT,
            first_name="Ananya",
            last_name="Sharma",
            is_verified=True,
        )
        ananya_profile, _ = StudentProfile.objects.update_or_create(
            user=ananya,
            defaults={
                "student_id": "SCDS-2023-019",
                "department": "Data Science",
                "degree_programme": "B.Tech",
                "graduation_year": 2027,
                "cgpa": Decimal("9.20"),
                "skills": [
                    "Python",
                    "SQL",
                    "Machine Learning",
                    "PyTorch",
                    "Data Analysis",
                    "FastAPI",
                ],
                "areas_of_interest": ["Applied AI", "Machine Learning", "Data Engineering"],
                "experience": "Undergraduate Research Assistant in NLP and Graph Neural Networks.",
                "preferred_roles": ["Data Scientist", "ML Engineer"],
                "preferred_locations": ["Bengaluru", "Mumbai", "Remote"],
                "work_mode": "REMOTE",
            },
        )
        if not ananya_profile.has_resume:
            ananya_profile.resume.save("ananya_resume.pdf", ContentFile(MINIMAL_PDF), save=True)

        # 3. Recruiter Accounts & Companies
        arjun_recruiter = _upsert_user(
            username="arjun_recruiter",
            email="arjun.mehta@novatech.io",
            role=User.Role.RECRUITER,
            first_name="Arjun",
            last_name="Mehta",
            is_verified=True,
        )
        novatech, _ = Company.objects.update_or_create(
            name="NovaTech Cloud Systems",
            defaults={
                "website": "https://novatech.example.com",
                "industry": "Cloud Infrastructure & Enterprise SaaS",
                "contact_email": "careers@novatech.io",
                "contact_phone": "+91-80-4123-9000",
                "description": "NovaTech builds cloud-native developer platforms, Kubernetes observability tools, and high-throughput data pipelines for global enterprises.",
                "verification_status": Company.VerificationStatus.VERIFIED,
                "verified_by": ipc_admin,
                "verified_at": now - timedelta(days=14),
                "reviewed_by": ipc_admin,
                "reviewed_at": now - timedelta(days=14),
            },
        )
        RecruiterProfile.objects.update_or_create(
            user=arjun_recruiter,
            defaults={
                "company": novatech,
                "designation": "University Talent Acquisition Lead",
                "work_email": "arjun.mehta@novatech.io",
                "contact_phone": "+91-98450-11223",
            },
        )

        kavya_recruiter = _upsert_user(
            username="kavya_recruiter",
            email="kavya.nair@quantumscale.ai",
            role=User.Role.RECRUITER,
            first_name="Kavya",
            last_name="Nair",
            is_verified=True,
        )
        quantumscale, _ = Company.objects.update_or_create(
            name="QuantumScale Analytics",
            defaults={
                "website": "https://quantumscale.example.com",
                "industry": "Artificial Intelligence & Data Analytics",
                "contact_email": "talent@quantumscale.ai",
                "contact_phone": "+91-44-6789-2200",
                "description": "QuantumScale delivers enterprise decision intelligence, real-time ML inference engines, and quantitative analytics.",
                "verification_status": Company.VerificationStatus.VERIFIED,
                "verified_by": ipc_admin,
                "verified_at": now - timedelta(days=10),
                "reviewed_by": ipc_admin,
                "reviewed_at": now - timedelta(days=10),
            },
        )
        RecruiterProfile.objects.update_or_create(
            user=kavya_recruiter,
            defaults={
                "company": quantumscale,
                "designation": "Engineering Hiring Manager",
                "work_email": "kavya.nair@quantumscale.ai",
                "contact_phone": "+91-98401-44556",
            },
        )

        # Pending company for IPC Admin review queue
        priya_recruiter = _upsert_user(
            username="priya_recruiter",
            email="priya.k@finpulse.io",
            role=User.Role.RECRUITER,
            first_name="Priya",
            last_name="Kulkarni",
            is_verified=True,
        )
        finpulse, _ = Company.objects.update_or_create(
            name="FinPulse Digital Payments",
            defaults={
                "website": "https://finpulse.example.com",
                "industry": "FinTech & Payment Systems",
                "contact_email": "campus@finpulse.io",
                "contact_phone": "+91-22-5500-8800",
                "description": "Real-time cross-border payment rails and fraud detection APIs for modern commerce.",
                "verification_status": Company.VerificationStatus.PENDING,
            },
        )
        RecruiterProfile.objects.update_or_create(
            user=priya_recruiter,
            defaults={
                "company": finpulse,
                "designation": "Campus Recruitment Specialist",
                "work_email": "priya.k@finpulse.io",
                "contact_phone": "+91-98201-77889",
            },
        )

        # 4. Opportunities (Published, Pending Approval, Draft)
        opportunities_spec = [
            {
                "title": "Full-Stack Software Engineer (New Grad 2027)",
                "company": novatech,
                "created_by": arjun_recruiter,
                "approved_by": ipc_admin,
                "opportunity_type": Opportunity.OpportunityType.JOB,
                "work_mode": Opportunity.WorkMode.HYBRID,
                "location": "Bengaluru",
                "compensation": Decimal("1850000.00"),
                "application_deadline": now + timedelta(days=35),
                "start_date": (now + timedelta(days=90)).date(),
                "application_method": "PLATFORM",
                "external_application_url": "",
                "status": Opportunity.Status.PUBLISHED,
                "published_at": now - timedelta(days=7),
                "approved_at": now - timedelta(days=7),
                "required_skills": ["Python", "Django", "React", "TypeScript", "PostgreSQL"],
                "eligibility_criteria": {
                    "minimum_cgpa": 7.5,
                    "graduation_years": [2027],
                    "degree_programmes": ["B.Tech"],
                    "departments": ["Computer Science", "Data Science"],
                },
                "description": (
                    "Join NovaTech's Core Platform team to architect and scale full-stack product features "
                    "serving over 500 enterprise customers. You will build resilient Django REST APIs, "
                    "responsive React/TypeScript interfaces, and PostgreSQL data models."
                ),
            },
            {
                "title": "Cloud & Kubernetes Site Reliability Intern",
                "company": novatech,
                "created_by": arjun_recruiter,
                "approved_by": ipc_admin,
                "opportunity_type": Opportunity.OpportunityType.INTERNSHIP,
                "work_mode": Opportunity.WorkMode.REMOTE,
                "location": "Remote",
                "compensation": Decimal("65000.00"),
                "application_deadline": now + timedelta(days=28),
                "start_date": (now + timedelta(days=45)).date(),
                "application_method": "PLATFORM",
                "external_application_url": "",
                "status": Opportunity.Status.PUBLISHED,
                "published_at": now - timedelta(days=5),
                "approved_at": now - timedelta(days=5),
                "required_skills": ["Docker", "Kubernetes", "Python"],
                "eligibility_criteria": {
                    "minimum_cgpa": 7.0,
                    "graduation_years": [2027, 2028],
                    "degree_programmes": ["B.Tech"],
                    "departments": ["Computer Science", "Data Science"],
                },
                "description": (
                    "Work with our Infrastructure & SRE group on multi-cluster Kubernetes automation, "
                    "CI/CD pipelines, container security hardening, and observability dashboards."
                ),
            },
            {
                "title": "Backend Platform Engineer - Distributed Systems",
                "company": novatech,
                "created_by": arjun_recruiter,
                "approved_by": ipc_admin,
                "opportunity_type": Opportunity.OpportunityType.JOB,
                "work_mode": Opportunity.WorkMode.ONSITE,
                "location": "Chennai",
                "compensation": Decimal("2100000.00"),
                "application_deadline": now + timedelta(days=42),
                "start_date": (now + timedelta(days=100)).date(),
                "application_method": "PLATFORM",
                "external_application_url": "",
                "status": Opportunity.Status.PUBLISHED,
                "published_at": now - timedelta(days=4),
                "approved_at": now - timedelta(days=4),
                "required_skills": ["Python", "PostgreSQL", "Docker", "SQL"],
                "eligibility_criteria": {
                    "minimum_cgpa": 8.0,
                    "graduation_years": [2027],
                    "degree_programmes": ["B.Tech"],
                    "departments": ["Computer Science", "Data Science"],
                },
                "description": (
                    "Design low-latency microservices, event-driven ingestion pipelines, and high-availability "
                    "PostgreSQL storage engines in our Chennai R&D center."
                ),
            },
            {
                "title": "Data Science & Applied ML Intern",
                "company": quantumscale,
                "created_by": kavya_recruiter,
                "approved_by": ipc_admin,
                "opportunity_type": Opportunity.OpportunityType.INTERNSHIP,
                "work_mode": Opportunity.WorkMode.HYBRID,
                "location": "Bengaluru",
                "compensation": Decimal("75000.00"),
                "application_deadline": now + timedelta(days=30),
                "start_date": (now + timedelta(days=50)).date(),
                "application_method": "PLATFORM",
                "external_application_url": "",
                "status": Opportunity.Status.PUBLISHED,
                "published_at": now - timedelta(days=6),
                "approved_at": now - timedelta(days=6),
                "required_skills": ["Python", "SQL"],
                "eligibility_criteria": {
                    "minimum_cgpa": 8.0,
                    "graduation_years": [2027],
                    "degree_programmes": ["B.Tech"],
                    "departments": ["Computer Science", "Data Science"],
                },
                "description": (
                    "Partner with senior data scientists to train, evaluate, and deploy predictive models "
                    "and feature pipelines for real-time enterprise forecasting."
                ),
            },
            {
                "title": "Frontend Design Systems Engineer",
                "company": quantumscale,
                "created_by": kavya_recruiter,
                "approved_by": ipc_admin,
                "opportunity_type": Opportunity.OpportunityType.JOB,
                "work_mode": Opportunity.WorkMode.REMOTE,
                "location": "Remote",
                "compensation": Decimal("1650000.00"),
                "application_deadline": now + timedelta(days=50),
                "start_date": (now + timedelta(days=75)).date(),
                "application_method": "EXTERNAL",
                "external_application_url": "https://quantumscale.example.com/careers/frontend-design-systems",
                "status": Opportunity.Status.PUBLISHED,
                "published_at": now - timedelta(days=3),
                "approved_at": now - timedelta(days=3),
                "required_skills": ["React", "TypeScript"],
                "eligibility_criteria": {
                    "minimum_cgpa": 7.0,
                    "graduation_years": [2027],
                    "degree_programmes": ["B.Tech"],
                    "departments": ["Computer Science", "Data Science"],
                },
                "description": (
                    "Build accessible, high-performance UI component libraries and interactive analytics "
                    "visualizations using React 19 and TypeScript."
                ),
            },
            {
                "title": "Quantitative Machine Learning Researcher",
                "company": quantumscale,
                "created_by": kavya_recruiter,
                "approved_by": ipc_admin,
                "opportunity_type": Opportunity.OpportunityType.JOB,
                "work_mode": Opportunity.WorkMode.ONSITE,
                "location": "Hyderabad",
                "compensation": Decimal("2400000.00"),
                "application_deadline": now + timedelta(days=45),
                "start_date": (now + timedelta(days=95)).date(),
                "application_method": "PLATFORM",
                "external_application_url": "",
                "status": Opportunity.Status.PUBLISHED,
                "published_at": now - timedelta(days=2),
                "approved_at": now - timedelta(days=2),
                "required_skills": ["Python", "Machine Learning", "PyTorch", "SQL"],
                "eligibility_criteria": {
                    "minimum_cgpa": 9.0,
                    "graduation_years": [2027],
                    "degree_programmes": ["B.Tech"],
                    "departments": ["Data Science"],
                },
                "description": (
                    "Research and productionize deep learning architectures for time-series forecasting "
                    "and anomaly detection on petabyte-scale datasets."
                ),
            },
            {
                "title": "AI Platform Security Engineer Intern",
                "company": novatech,
                "created_by": arjun_recruiter,
                "approved_by": None,
                "opportunity_type": Opportunity.OpportunityType.INTERNSHIP,
                "work_mode": Opportunity.WorkMode.HYBRID,
                "location": "Bengaluru",
                "compensation": Decimal("70000.00"),
                "application_deadline": now + timedelta(days=40),
                "start_date": (now + timedelta(days=60)).date(),
                "application_method": "PLATFORM",
                "external_application_url": "",
                "status": Opportunity.Status.PENDING_APPROVAL,
                "published_at": None,
                "approved_at": None,
                "required_skills": ["Python", "Docker", "Kubernetes"],
                "eligibility_criteria": {
                    "minimum_cgpa": 7.5,
                    "graduation_years": [2027],
                    "degree_programmes": ["B.Tech"],
                    "departments": ["Computer Science"],
                },
                "description": (
                    "Pending IPC approval: Assist our Security Engineering team with container runtime "
                    "attestation, API gateway rate-limiting, and automated vulnerability scanning."
                ),
            },
            {
                "title": "Developer Experience Engineer (Draft)",
                "company": novatech,
                "created_by": arjun_recruiter,
                "approved_by": None,
                "opportunity_type": Opportunity.OpportunityType.JOB,
                "work_mode": Opportunity.WorkMode.REMOTE,
                "location": "Remote",
                "compensation": Decimal("1750000.00"),
                "application_deadline": now + timedelta(days=55),
                "start_date": (now + timedelta(days=85)).date(),
                "application_method": "PLATFORM",
                "external_application_url": "",
                "status": Opportunity.Status.DRAFT,
                "published_at": None,
                "approved_at": None,
                "required_skills": ["TypeScript", "Python", "Docker"],
                "eligibility_criteria": {
                    "minimum_cgpa": 7.5,
                    "graduation_years": [2027],
                    "degree_programmes": ["B.Tech"],
                    "departments": ["Computer Science", "Data Science"],
                },
                "description": (
                    "Draft listing ready for recruiter submission: Build CLI tooling, SDKs, and developer "
                    "portals for NovaTech's cloud ecosystem."
                ),
            },
        ]

        created_opportunities = {}
        for spec in opportunities_spec:
            opp, _ = Opportunity.objects.update_or_create(
                title=spec["title"],
                company=spec["company"],
                defaults=spec,
            )
            created_opportunities[spec["title"]] = opp

        # Workflow Audit Events for realism
        WorkflowAuditEvent.objects.get_or_create(
            actor=ipc_admin,
            object_type=WorkflowAuditEvent.ObjectType.COMPANY,
            object_id=novatech.id,
            action=WorkflowAuditEvent.Action.COMPANY_VERIFIED,
            defaults={"details": {"company_name": novatech.name}},
        )

        # 5. Student Applications & Notifications
        opp_fullstack = created_opportunities["Full-Stack Software Engineer (New Grad 2027)"]
        opp_sre = created_opportunities["Cloud & Kubernetes Site Reliability Intern"]

        for opp, target_status, note_text in [
            (
                opp_fullstack,
                Application.Status.SHORTLISTED,
                "Shortlisted for technical round after strong full-stack and system design review.",
            ),
            (
                opp_sre,
                Application.Status.SUBMITTED,
                "Application submitted.",
            ),
        ]:
            snapshot = evaluate_eligibility(opp, rahul_profile)
            app, created = Application.objects.get_or_create(
                student=rahul,
                opportunity=opp,
                defaults={
                    "status": target_status,
                    "eligibility_snapshot": snapshot,
                },
            )
            if not app.resume:
                app.resume.save(f"app_{rahul.username}_{opp.id}.pdf", ContentFile(MINIMAL_PDF), save=True)
            if app.status != target_status:
                app.status = target_status
                app.save(update_fields=["status"])

            if not app.status_history.exists():
                ApplicationStatusHistory.objects.create(
                    application=app,
                    status=Application.Status.SUBMITTED,
                    changed_by=rahul,
                    note="Application submitted.",
                )
                if target_status != Application.Status.SUBMITTED:
                    ApplicationStatusHistory.objects.create(
                        application=app,
                        status=target_status,
                        changed_by=arjun_recruiter,
                        note=note_text,
                    )

            Notification.objects.get_or_create(
                recipient=rahul,
                notification_type=Notification.NotificationType.APPLICATION_SUBMITTED,
                application=app,
                defaults={
                    "title": f"Application submitted: {opp.title}",
                    "message": f"Your application for {opp.title} at {opp.company.name} has been recorded.",
                },
            )

        # 6. Alumni Accounts, Profiles & Referral Workflows
        vikram_alumni = _upsert_user(
            username="vikram_alumni",
            email="vikram.rao@alumni.saiuniversity.edu.in",
            role=User.Role.ALUMNI,
            first_name="Vikram",
            last_name="Rao",
            is_verified=True,
        )
        vikram_profile, _ = AlumniProfile.objects.update_or_create(
            user=vikram_alumni,
            defaults={
                "department": "Computer Science",
                "degree_programme": "B.Tech",
                "graduation_year": 2023,
                "current_company": "Google",
                "designation": "Senior Software Engineer",
                "industry": "Cloud & Distributed Systems",
                "is_open_to_referrals": True,
                "verification_status": AlumniProfile.VerificationStatus.VERIFIED,
                "verified_by": ipc_admin,
                "verified_at": now - timedelta(days=20),
                "reviewed_by": ipc_admin,
                "reviewed_at": now - timedelta(days=20),
            },
        )
        if not vikram_profile.graduation_proof:
            vikram_profile.graduation_proof.save("vikram_degree.pdf", ContentFile(MINIMAL_PDF), save=True)

        meera_alumni = _upsert_user(
            username="meera_alumni",
            email="meera.k@alumni.saiuniversity.edu.in",
            role=User.Role.ALUMNI,
            first_name="Meera",
            last_name="Krishnan",
            is_verified=True,
        )
        meera_profile, _ = AlumniProfile.objects.update_or_create(
            user=meera_alumni,
            defaults={
                "department": "Data Science",
                "degree_programme": "B.Tech",
                "graduation_year": 2024,
                "current_company": "Microsoft",
                "designation": "Applied Scientist II",
                "industry": "Artificial Intelligence",
                "is_open_to_referrals": True,
                "verification_status": AlumniProfile.VerificationStatus.VERIFIED,
                "verified_by": ipc_admin,
                "verified_at": now - timedelta(days=15),
                "reviewed_by": ipc_admin,
                "reviewed_at": now - timedelta(days=15),
            },
        )
        if not meera_profile.graduation_proof:
            meera_profile.graduation_proof.save("meera_degree.pdf", ContentFile(MINIMAL_PDF), save=True)

        # Pending alumni verification for IPC Admin dashboard
        rohan_alumni = _upsert_user(
            username="rohan_alumni",
            email="rohan.desai@alumni.saiuniversity.edu.in",
            role=User.Role.ALUMNI,
            first_name="Rohan",
            last_name="Desai",
            is_verified=False,
        )
        rohan_profile, _ = AlumniProfile.objects.update_or_create(
            user=rohan_alumni,
            defaults={
                "department": "Computer Science",
                "degree_programme": "B.Tech",
                "graduation_year": 2024,
                "current_company": "Stripe",
                "designation": "Infrastructure Engineer",
                "industry": "FinTech",
                "is_open_to_referrals": True,
                "verification_status": AlumniProfile.VerificationStatus.PENDING,
            },
        )
        if not rohan_profile.graduation_proof:
            rohan_profile.graduation_proof.save("rohan_degree.pdf", ContentFile(MINIMAL_PDF), save=True)

        # Referral request 1: Rahul -> Vikram (ACCEPTED)
        ref1, _ = ReferralRequest.objects.get_or_create(
            student=rahul,
            alumni_profile=vikram_profile,
            opportunity_url="https://careers.google.com/jobs/results/102938-software-engineer-university-grad/",
            defaults={
                "note": "Hi Vikram! I am a final-year CS student at Sai University (CGPA 8.95) with experience in Python, Go, Kubernetes, and distributed systems. Would love to be considered for a referral!",
                "status": ReferralRequest.Status.ACCEPTED,
            },
        )
        if not ref1.resume:
            ref1.resume.save("rahul_referral_resume.pdf", ContentFile(MINIMAL_PDF), save=True)
        if not ref1.history.exists():
            ReferralRequestHistory.objects.create(
                referral_request=ref1,
                event=ReferralRequestHistory.Event.REQUESTED,
                previous_status="",
                new_status=ReferralRequest.Status.PENDING,
                changed_by=rahul,
                note=ref1.note,
            )
            ReferralRequestHistory.objects.create(
                referral_request=ref1,
                event=ReferralRequestHistory.Event.ACCEPTED,
                previous_status=ReferralRequest.Status.PENDING,
                new_status=ReferralRequest.Status.ACCEPTED,
                changed_by=vikram_alumni,
                note="Strong systems background and project portfolio. Happy to refer you this week!",
            )

        Notification.objects.get_or_create(
            recipient=rahul,
            notification_type=Notification.NotificationType.REFERRAL_STATUS,
            referral_request=ref1,
            defaults={
                "title": "Referral request accepted by Vikram Rao",
                "message": "Vikram Rao (Google) accepted your referral request and left a note.",
            },
        )

        # Referral request 2: Ananya -> Vikram (PENDING - so Vikram can act on it in the demo)
        ref2, _ = ReferralRequest.objects.get_or_create(
            student=ananya,
            alumni_profile=vikram_profile,
            opportunity_url="https://careers.google.com/jobs/results/204912-machine-learning-intern/",
            defaults={
                "note": "Hello Vikram! I am researching Graph Neural Networks and NLP at Sai University (CGPA 9.20). I would really appreciate a referral for the ML Internship role.",
                "status": ReferralRequest.Status.PENDING,
            },
        )
        if not ref2.resume:
            ref2.resume.save("ananya_referral_resume.pdf", ContentFile(MINIMAL_PDF), save=True)
        if not ref2.history.exists():
            ReferralRequestHistory.objects.create(
                referral_request=ref2,
                event=ReferralRequestHistory.Event.REQUESTED,
                previous_status="",
                new_status=ReferralRequest.Status.PENDING,
                changed_by=ananya,
                note=ref2.note,
            )

        Notification.objects.get_or_create(
            recipient=vikram_alumni,
            notification_type=Notification.NotificationType.REFERRAL_REQUEST,
            referral_request=ref2,
            defaults={
                "title": "New referral request from Ananya Sharma",
                "message": "Ananya Sharma requested a referral for Google Machine Learning Intern.",
            },
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded Nexus Career demo data successfully (password for all demo users: {DEMO_PASSWORD})"
            )
        )
        for u in [rahul, ananya, arjun_recruiter, kavya_recruiter, priya_recruiter, vikram_alumni, meera_alumni, rohan_alumni, ipc_admin, sys_admin]:
            self.stdout.write(f"  - {u.role:12s} | username: {u.username:18s} | email: {u.email}")
