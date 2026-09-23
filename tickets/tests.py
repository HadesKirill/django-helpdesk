from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

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