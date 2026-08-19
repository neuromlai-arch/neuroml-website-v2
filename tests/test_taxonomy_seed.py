"""Locks in the real service/industry/technology taxonomy seed_demo now
produces, replacing the old placeholder set. Data-only change — no model
changes — so these are seed_demo output contracts, not model tests."""

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from solutions.models import Service, Technology
from taxonomy.models import Industry, ServiceCluster


class TaxonomySeedTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo")

    def test_three_clusters_in_order(self):
        clusters = list(ServiceCluster.objects.order_by("order").values_list("name", "order"))
        self.assertEqual(clusters, [
            ("AI & Machine Learning", 1),
            ("Product Engineering", 2),
            ("Growth", 3),
        ])

    def test_eleven_services_all_top_level(self):
        self.assertEqual(Service.objects.count(), 11)
        self.assertEqual(Service.objects.filter(parent__isnull=False).count(), 0)

    def test_nine_services_show_in_form_dropdown(self):
        dropdown_services = set(
            Service.objects.filter(show_in_form_dropdown=True).values_list("title", flat=True)
        )
        self.assertEqual(len(dropdown_services), 9)
        self.assertEqual(
            dropdown_services,
            {
                "AI Agents & Automation", "RAG & Knowledge Systems",
                "LLM Application Development", "Computer Vision",
                "ML Engineering & MLOps", "Full-Stack Development",
                "Custom Software Development", "DevOps & Cloud",
                "Salesforce Development",
            },
        )

    def test_growth_services_excluded_from_form_dropdown(self):
        growth = ServiceCluster.objects.get(name="Growth")
        self.assertFalse(
            Service.objects.filter(cluster=growth, show_in_form_dropdown=True).exists()
        )
        self.assertEqual(
            set(Service.objects.filter(cluster=growth).values_list("title", flat=True)),
            {"SEO", "Digital Marketing"},
        )

    def test_service_taglines_are_final_copy_not_placeholder(self):
        service = Service.objects.get(title="AI Agents & Automation")
        self.assertEqual(service.tagline, "Autonomous agents that do real work, not demos")
        self.assertNotIn("[TODO]", service.tagline)
        self.assertNotIn("[Placeholder]", service.tagline)

    def test_service_body_and_summary_are_marked_todo(self):
        for service in Service.objects.all():
            with self.subTest(service=service.title):
                self.assertTrue(service.summary.startswith("[TODO]"))
                self.assertIn("[TODO]", service.body)

    def test_six_industries(self):
        names = set(Industry.objects.values_list("name", flat=True))
        self.assertEqual(names, {
            "iGaming & Sweepstakes", "E-commerce & Retail", "Fintech",
            "Healthcare", "Logistics & Supply Chain", "SaaS & Startups",
        })

    def test_nineteen_technologies_mapped_to_real_services(self):
        self.assertEqual(Technology.objects.count(), 19)
        expected = {
            "Python": "Full-Stack Development", "FastAPI": "Full-Stack Development",
            "Django": "Full-Stack Development", "NestJS": "Full-Stack Development",
            "React": "Full-Stack Development", "Next.js": "Full-Stack Development",
            "React Native": "Full-Stack Development",
            "LangChain": "AI Agents & Automation", "LangGraph": "AI Agents & Automation",
            "OpenAI API": "LLM Application Development",
            "Anthropic API": "LLM Application Development",
            "PyTorch": "Computer Vision", "YOLO": "Computer Vision",
            "AWS": "DevOps & Cloud", "GCP": "DevOps & Cloud",
            "Docker": "DevOps & Cloud", "Kubernetes": "DevOps & Cloud",
            "PostgreSQL": "Custom Software Development",
            "Redis": "Custom Software Development",
        }
        actual = {t.name: t.service.title for t in Technology.objects.select_related("service")}
        self.assertEqual(actual, expected)

    def test_first_twelve_technologies_show_in_stack_grid(self):
        in_grid = set(
            Technology.objects.filter(show_in_stack_grid=True).order_by("order").values_list("name", flat=True)
        )
        self.assertEqual(len(in_grid), 12)
        self.assertIn("Python", in_grid)
        self.assertIn("PyTorch", in_grid)
        self.assertNotIn("YOLO", in_grid)
        self.assertNotIn("Redis", in_grid)


class MegamenuRendersAllClustersTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo")

    def test_homepage_megamenu_shows_all_three_clusters_with_their_services(self):
        from django.utils.html import escape

        response = self.client.get(reverse("home"))
        for cluster_name in ("AI & Machine Learning", "Product Engineering", "Growth"):
            self.assertContains(response, escape(cluster_name))
        for service_title in (
            "AI Agents & Automation", "Full-Stack Development", "SEO",
        ):
            self.assertContains(response, escape(service_title))
        # Growth's services must appear in the nav even though they're
        # excluded from the contact form dropdown.
        self.assertContains(response, escape("Digital Marketing"))


class ContactFormServiceDropdownTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo")

    def test_dropdown_has_exactly_nine_options_grouped_by_cluster(self):
        response = self.client.get(reverse("contact"))
        form = response.context["form"]
        field = form.fields["service_interest"]
        # field.choices is the optgroup structure built in ContactSubmissionBaseForm.__init__:
        # [("", "Select a service"), (cluster_name, [(pk, title), ...]), ...]
        groups = {label: [title for _, title in options] for label, options in field.choices[1:]}
        self.assertEqual(set(groups.keys()), {"AI & Machine Learning", "Product Engineering"})
        self.assertNotIn("Growth", groups)
        total_options = sum(len(titles) for titles in groups.values())
        self.assertEqual(total_options, 9)
        self.assertEqual(len(groups["AI & Machine Learning"]), 5)
        self.assertEqual(len(groups["Product Engineering"]), 4)

    def test_dropdown_rendered_html_has_two_optgroups_and_nine_options(self):
        response = self.client.get(reverse("contact"))
        html = response.content.decode()
        self.assertEqual(html.count("<optgroup"), 2)
        self.assertContains(response, 'label="AI &amp; Machine Learning"')
        self.assertContains(response, 'label="Product Engineering"')
        self.assertNotContains(response, 'label="Growth"')
