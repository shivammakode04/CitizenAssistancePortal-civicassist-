from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.text import slugify


class Department(models.Model):
    """
    Master table for all departments used in routing and picklists.
    """

    code = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=255)
    category = models.CharField(
        max_length=32,
        choices=(
            ("Municipal", "Municipal"),
            ("State", "State"),
            ("Police", "Police"),
            ("District", "District"),
            ("Judicial", "Judicial"),
            ("Helpline", "Helpline"),
        ),
    )
    problems_covered = models.TextField()
    is_helpline = models.BooleanField(default=False)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.code})"


class Complaint(models.Model):
    """
    Citizen complaint routed to a specific department.
    """

    PRIORITY_CHOICES = (
        ("LOW", "Low"),
        ("MEDIUM", "Medium"),
        ("HIGH", "High"),
        ("CRITICAL", "Critical"),
    )

    STATUS_CHOICES = (
        ("OPEN", "Open"),
        ("CLOSED", "Closed"),
        ("REOPENED", "Reopened"),
        ("TRANSFERRED", "Transferred"),
    )

    ticket_number = models.CharField(max_length=50, unique=True, editable=False)
    citizen = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="complaints"
    )
    department = models.ForeignKey(
        Department, on_delete=models.PROTECT, related_name="complaints"
    )
    description = models.TextField()
    location = models.CharField(max_length=255)
    city = models.CharField(max_length=100, blank=True)
    pincode = models.CharField(max_length=10, blank=True)
    district = models.CharField(max_length=100, blank=True)
    # Optional photo evidence uploaded by the citizen.
    image = models.ImageField(
        upload_to="complaint_images/", null=True, blank=True
    )
    priority = models.CharField(max_length=16, choices=PRIORITY_CHOICES)
    status = models.CharField(
        max_length=16, choices=STATUS_CHOICES, default="OPEN", db_index=True
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    original_department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        related_name="original_complaints",
        null=True,
        blank=True,
    )

    def save(self, *args, **kwargs):
        """
        Ensure a ticket number is generated once on first save.
        """
        creating = self.pk is None
        if creating and not self.ticket_number:
            self.ticket_number = self._generate_ticket_number()
        if creating and self.original_department is None:
            self.original_department = self.department
        super().save(*args, **kwargs)

    def _generate_ticket_number(self) -> str:
        """
        Generate a unique ticket number based on the *original*
        department code, regardless of later transfers.

        Example: MC-PWD-00001
        """
        # Always use the original routing department for the prefix
        dept_for_code = self.original_department or self.department
        base_code = slugify(dept_for_code.code).upper().replace("-", "")
        if not base_code:
            base_code = "GEN"

        # Look at all complaints whose ticket number already uses this prefix,
        # even if they were later transferred to a different department.
        prefix = f"{base_code}-"
        last = Complaint.objects.filter(ticket_number__startswith=prefix).order_by("-id").first()

        next_number = 1
        if last and last.ticket_number:
            try:
                suffix = last.ticket_number.split("-")[-1]
                next_number = int(suffix) + 1
            except (ValueError, IndexError):
                next_number = last.id + 1
        return f"{base_code}-{next_number:05d}"

    def __str__(self) -> str:
        return f"{self.ticket_number} - {self.department.name}"


class Notification(models.Model):
    """
    Simple notification for user actions like complaint closure.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications"
    )
    complaint = models.ForeignKey(
        Complaint,
        on_delete=models.CASCADE,
        related_name="notifications",
        null=True,
        blank=True,
    )
    message = models.CharField(max_length=255)
    created_at = models.DateTimeField(default=timezone.now)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Notification for {self.user.email}: {self.message}"


class ComplaintHistory(models.Model):
    """
    Immutable audit log of important complaint events
    (creation, status changes, transfers, escalations).
    """

    complaint = models.ForeignKey(
        Complaint, on_delete=models.CASCADE, related_name="history"
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="complaint_history_events",
    )
    action = models.CharField(max_length=64)
    from_status = models.CharField(max_length=16, blank=True)
    to_status = models.CharField(max_length=16, blank=True)
    from_department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    to_department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.complaint.ticket_number} - {self.action} at {self.created_at}"


DEPARTMENT_SEED_DATA = [
    {
        "code": "MC-PWD",
        "name": "Municipal Corporation - Public Works Department",
        "category": "Municipal",
        "problems_covered": "Municipal roads, potholes, footpaths, streetlights",
    },
    {
        "code": "MC-WATER",
        "name": "Municipal Corporation - Water Supply Department",
        "category": "Municipal",
        "problems_covered": "Water shortage, leakage, low pressure",
    },
    {
        "code": "MC-SWM",
        "name": "Municipal Corporation - Solid Waste Management",
        "category": "Municipal",
        "problems_covered": "Garbage collection, street cleaning",
    },
    {
        "code": "MC-HEALTH",
        "name": "Municipal Corporation - Health Department",
        "category": "Municipal",
        "problems_covered": "Dispensaries, mosquito control, sanitation",
    },
    {
        "code": "MC-SEWER",
        "name": "Municipal Corporation - Sewerage & Drainage",
        "category": "Municipal",
        "problems_covered": "Manhole cleaning, waterlogging",
    },
    {
        "code": "MC-FIRE",
        "name": "Municipal Fire Department",
        "category": "Municipal",
        "problems_covered": "Fire tenders, hydrants, safety",
    },
    {
        "code": "MC-TP",
        "name": "Municipal Town Planning Department",
        "category": "Municipal",
        "problems_covered": "Building permissions, encroachments",
    },
    {
        "code": "MC-PARK",
        "name": "Municipal Parks & Gardens Department",
        "category": "Municipal",
        "problems_covered": "Park maintenance, playgrounds",
    },
    {
        "code": "STATE-ELEC",
        "name": "State Electricity Distribution Company",
        "category": "State",
        "problems_covered": "Power cuts, transformers, billing",
    },
    {
        "code": "STATE-PHED",
        "name": "Public Health Engineering Department (PHED)",
        "category": "State",
        "problems_covered": "Water schemes, contamination",
    },
    {
        "code": "STATE-PWD",
        "name": "Public Works Department (PWD) - Roads",
        "category": "State",
        "problems_covered": "Highways, bridges, signage",
    },
    {
        "code": "POLICE-TRAF",
        "name": "Traffic Police Department",
        "category": "Police",
        "problems_covered": "Signals, parking, traffic management",
    },
    {
        "code": "DIST-HEALTH",
        "name": "District Health Department",
        "category": "District",
        "problems_covered": "Government hospitals, ambulances",
    },
    {
        "code": "STATE-POLL",
        "name": "State Pollution Control Board",
        "category": "State",
        "problems_covered": "Industrial pollution, noise, dust",
    },
    {
        "code": "STATE-FCS",
        "name": "Food & Civil Supplies Department",
        "category": "State",
        "problems_covered": "Ration distribution, PDS shops",
    },
    {
        "code": "POLICE-LOCAL",
        "name": "Local Police Department",
        "category": "Police",
        "problems_covered": "Patrolling, safety, petty crimes",
    },
    {
        "code": "JUD-CONS",
        "name": "Consumer Grievance Forum",
        "category": "Judicial",
        "problems_covered": "Billing disputes, service issues",
    },
    {
        "code": "DIST-REV",
        "name": "District Revenue Department",
        "category": "District",
        "problems_covered": "Land records, property tax",
    },
    {
        "code": "HELP",
        "name": "Helpline Department",
        "category": "Helpline",
        "problems_covered": "General helpline and misrouted complaints",
        "is_helpline": True,
    },
]


def ensure_departments_seeded() -> None:
    """
    Idempotent helper to ensure all master departments exist.
    Safe to call from views before using Department picklists.
    """
    for row in DEPARTMENT_SEED_DATA:
        defaults = {
            "name": row["name"],
            "category": row["category"],
            "problems_covered": row["problems_covered"],
            "is_helpline": row.get("is_helpline", False),
        }
        Department.objects.update_or_create(code=row["code"], defaults=defaults)


def auto_escalate_overdue_complaints(max_age_hours: int = 48) -> int:
    """
    Transfer overdue complaints to the Helpline department based on SLA.

    This is a lightweight, on-request SLA engine:
    - Called from dashboards so no background worker is required.
    - Finds complaints that are OPEN / REOPENED / TRANSFERRED
      and older than max_age_hours and moves them to Helpline.
    - Returns the number of complaints escalated in this call.
    """
    helpline = Department.objects.filter(is_helpline=True).first()
    if helpline is None:
        return 0

    cutoff = timezone.now() - timedelta(hours=max_age_hours)

    overdue = Complaint.objects.filter(
        created_at__lte=cutoff,
        status__in=["OPEN", "REOPENED", "TRANSFERRED"],
    ).exclude(department=helpline)

    count = 0
    for complaint in overdue.select_related("citizen"):
        from_department = complaint.department
        from_status = complaint.status

        complaint.department = helpline
        complaint.status = "TRANSFERRED"
        complaint.save(update_fields=["department", "status", "updated_at"])

        Notification.objects.create(
            user=complaint.citizen,
            complaint=complaint,
            message=(
                f"Complaint {complaint.ticket_number} was auto-escalated to "
                f"{helpline.name} due to no action within SLA."
            ),
        )

        ComplaintHistory.objects.create(
            complaint=complaint,
            actor=None,
            action="AUTO_ESCALATED",
            from_status=from_status,
            to_status=complaint.status,
            from_department=from_department,
            to_department=helpline,
            notes="Complaint auto-escalated to Helpline based on SLA.",
        )
        count += 1

    return count

