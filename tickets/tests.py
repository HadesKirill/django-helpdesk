from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from unittest.mock import patch

from .services import change_ticket_status
from .models import Category, Ticket

User = get_user_model()


class TicketListAccessTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.customer = User.objects.create_user(
            username="customer",
            role=User.Role.CUSTOMER,
        )
        cls.other_customer = User.objects.create_user(
            username="other_customer",
            role=User.Role.CUSTOMER,
        )
        cls.technician = User.objects.create_user(
            username="technician",
            role=User.Role.TECHNICIAN,
        )
        cls.other_technician = User.objects.create_user(
            username="other_technician",
            role=User.Role.TECHNICIAN,
        )
        cls.admin = User.objects.create_superuser(
            username="test_admin",
            password="test-only-password-482!",
        )
        category = Category.objects.create(name="Техника")

        cls.assigned_ticket = Ticket.objects.create(
            title="Заявка первого заказчика",
            description="Тестовая проблема",
            category=category,
            customer=cls.customer,
            assignee=cls.technician,
        )
        cls.other_ticket = Ticket.objects.create(
            title="Заявка другого заказчика",
            description="Другая проблема",
            category=category,
            customer=cls.other_customer,
            assignee=cls.other_technician,
        )
        cls.unassigned_ticket = Ticket.objects.create(
            title="Заявка без исполнителя",
            description="Ожидает назначения",
            category=category,
            customer=cls.customer,
        )

    def test_guest_is_redirected_to_login(self):
        url = reverse("tickets:list")
        response = self.client.get(url)

        self.assertRedirects(
            response,
            f"{reverse('login')}?next={url}",
        )

    def test_customer_sees_only_own_tickets(self):
        self.client.force_login(self.customer)
        response = self.client.get(reverse("tickets:list"))

        self.assertEqual(response.status_code, 200)
        self.assertCountEqual(
            response.context["tickets"],
            [self.assigned_ticket, self.unassigned_ticket],
        )
        self.assertNotContains(response, self.other_ticket.title)

    def test_technician_sees_only_assigned_tickets(self):
        self.client.force_login(self.technician)
        response = self.client.get(reverse("tickets:list"))

        self.assertEqual(response.status_code, 200)
        self.assertCountEqual(
            response.context["tickets"],
            [self.assigned_ticket],
        )
        self.assertNotContains(response, self.other_ticket.title)
        self.assertNotContains(response, self.unassigned_ticket.title)

    def test_superuser_sees_all_tickets(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("tickets:list"))

        self.assertEqual(response.status_code, 200)
        self.assertCountEqual(
            response.context["tickets"],
            [
                self.assigned_ticket,
                self.other_ticket,
                self.unassigned_ticket,
            ],
        )

    def test_detail_access_rules(self):
        cases = [
            (self.customer, 200),
            (self.technician, 200),
            (self.admin, 200),
            (self.other_customer, 404),
            (self.other_technician, 404),
        ]
        url = reverse(
            "tickets:detail",
            kwargs={"pk": self.assigned_ticket.pk},
        )

        for user, expected_status in cases:
            with self.subTest(user=user.username):
                self.client.force_login(user)
                response = self.client.get(url)

                self.assertEqual(
                    response.status_code,
                    expected_status,
                )

    def test_customer_cannot_override_protected_fields(self):
        self.client.force_login(self.customer)
        initial_count = Ticket.objects.count()

        response = self.client.post(
            reverse("tickets:create"),
            {
                "title": "Новая заявка через сайт",
                "description": "Не работает монитор",
                "category": self.assigned_ticket.category_id,
                "priority": Ticket.Priority.HIGH,
                "customer": self.other_customer.pk,
                "assignee": self.technician.pk,
                "status": Ticket.Status.CLOSED,
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            Ticket.objects.count(),
            initial_count + 1,
        )

        ticket = Ticket.objects.get(title="Новая заявка через сайт")

        self.assertEqual(ticket.customer_id, self.customer.pk)
        self.assertEqual(ticket.status, Ticket.Status.NEW)
        self.assertIsNone(ticket.assignee_id)
        self.assertEqual(ticket.priority, Ticket.Priority.HIGH)

        self.assertRedirects(
            response,
            reverse("tickets:detail", kwargs={"pk": ticket.pk}),
        )

    def test_technician_cannot_create_ticket(self):
        self.client.force_login(self.technician)
        url = reverse("tickets:create")
        initial_count = Ticket.objects.count()

        self.assertEqual(self.client.get(url).status_code, 403)

        response = self.client.post(
            url,
            {
                "title": "Недопустимая заявка",
                "description": "Попытка создания исполнителем",
                "category": self.assigned_ticket.category_id,
                "priority": Ticket.Priority.NORMAL,
            },
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(Ticket.objects.count(), initial_count)

    def test_invalid_form_does_not_create_ticket(self):
        self.client.force_login(self.customer)
        initial_count = Ticket.objects.count()

        response = self.client.post(
            reverse("tickets:create"),
            {
                "title": "",
                "description": "Описание без названия",
                "category": self.assigned_ticket.category_id,
                "priority": Ticket.Priority.NORMAL,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("title", response.context["form"].errors)
        self.assertEqual(Ticket.objects.count(), initial_count)

    def test_guest_cannot_open_create_or_detail(self):
        urls = [
            reverse("tickets:create"),
            reverse(
                "tickets:detail",
                kwargs={"pk": self.assigned_ticket.pk},
            ),
        ]

        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertRedirects(
                    response,
                    f"{reverse('login')}?next={url}",
                )
    def test_full_status_lifecycle(self):
        ticket = self.assigned_ticket
        url = reverse("tickets:status", kwargs={"pk": ticket.pk})

        steps = [
            (self.technician, Ticket.Status.IN_PROGRESS),
            (self.technician, Ticket.Status.RESOLVED),
            (self.customer, Ticket.Status.CLOSED),
        ]

        old_status = Ticket.Status.NEW

        for actor, new_status in steps:
            with self.subTest(status=new_status):
                self.client.force_login(actor)
                response = self.client.post(
                    url,
                    {"status": new_status},
                )

                self.assertRedirects(
                    response,
                    reverse("tickets:detail", kwargs={"pk": ticket.pk}),
                )

                ticket.refresh_from_db()
                self.assertEqual(ticket.status, new_status)

                event = ticket.status_history.first()
                self.assertEqual(event.actor_id, actor.pk)
                self.assertEqual(event.old_status, old_status)
                self.assertEqual(event.new_status, new_status)

                old_status = new_status

        self.assertEqual(ticket.status_history.count(), 3)

    def test_customer_cannot_start_work(self):
        ticket = self.assigned_ticket
        self.client.force_login(self.customer)

        response = self.client.post(
            reverse("tickets:status", kwargs={"pk": ticket.pk}),
            {"status": Ticket.Status.IN_PROGRESS},
        )

        self.assertEqual(response.status_code, 403)
        ticket.refresh_from_db()
        self.assertEqual(ticket.status, Ticket.Status.NEW)
        self.assertFalse(ticket.status_history.exists())

    def test_unrelated_technician_cannot_change_status(self):
        ticket = self.assigned_ticket
        self.client.force_login(self.other_technician)

        response = self.client.post(
            reverse("tickets:status", kwargs={"pk": ticket.pk}),
            {"status": Ticket.Status.IN_PROGRESS},
        )

        self.assertEqual(response.status_code, 404)
        ticket.refresh_from_db()
        self.assertEqual(ticket.status, Ticket.Status.NEW)
        self.assertFalse(ticket.status_history.exists())

    def test_cannot_skip_or_repeat_status_transition(self):
        ticket = self.assigned_ticket
        url = reverse("tickets:status", kwargs={"pk": ticket.pk})
        self.client.force_login(self.technician)

        response = self.client.post(
            url,
            {"status": Ticket.Status.RESOLVED},
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(ticket.status_history.exists())

        response = self.client.post(
            url,
            {"status": Ticket.Status.IN_PROGRESS},
        )
        self.assertEqual(response.status_code, 302)

        response = self.client.post(
            url,
            {"status": Ticket.Status.IN_PROGRESS},
        )
        self.assertEqual(response.status_code, 403)

        ticket.refresh_from_db()
        self.assertEqual(ticket.status, Ticket.Status.IN_PROGRESS)
        self.assertEqual(ticket.status_history.count(), 1)

    def test_get_request_cannot_change_status(self):
        ticket = self.assigned_ticket
        self.client.force_login(self.technician)

        response = self.client.get(
            reverse("tickets:status", kwargs={"pk": ticket.pk}),
            {"status": Ticket.Status.IN_PROGRESS},
        )

        self.assertEqual(response.status_code, 405)
        ticket.refresh_from_db()
        self.assertEqual(ticket.status, Ticket.Status.NEW)
        self.assertFalse(ticket.status_history.exists())

    def test_status_rolls_back_if_history_creation_fails(self):
        ticket = self.assigned_ticket

        with patch(
            "tickets.services.TicketStatusHistory.objects.create",
            side_effect=RuntimeError("Ошибка записи истории"),
        ):
            with self.assertRaises(RuntimeError):
                change_ticket_status(
                    ticket_id=ticket.pk,
                    actor=self.technician,
                    new_status=Ticket.Status.IN_PROGRESS,
                )

        ticket.refresh_from_db()
        self.assertEqual(ticket.status, Ticket.Status.NEW)
        self.assertFalse(ticket.status_history.exists())