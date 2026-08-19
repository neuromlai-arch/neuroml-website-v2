"""One sitemap section per published content type. Each class is a thin
wrapper around `Model.objects.live()` — nothing here duplicates query logic
that already lives on the model manager.
"""

from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from careers.models import JobPosting
from insights.models import BlogPost, CaseStudy, Handbook, Webinar
from solutions.models import HireRole, Product, Service, Technology, UseCase
from taxonomy.models import Industry


class PublishableSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.6
    model = None

    def items(self):
        return self.model.objects.live()

    def lastmod(self, obj):
        return obj.updated_at


class ServiceSitemap(PublishableSitemap):
    model = Service
    priority = 0.8


class UseCaseSitemap(PublishableSitemap):
    model = UseCase


class ProductSitemap(PublishableSitemap):
    model = Product
    priority = 0.7


class TechnologySitemap(PublishableSitemap):
    model = Technology


class HireRoleSitemap(PublishableSitemap):
    model = HireRole


class BlogPostSitemap(PublishableSitemap):
    model = BlogPost
    changefreq = "monthly"


class CaseStudySitemap(PublishableSitemap):
    model = CaseStudy
    priority = 0.7


class HandbookSitemap(PublishableSitemap):
    model = Handbook
    changefreq = "monthly"


class WebinarSitemap(PublishableSitemap):
    model = Webinar
    changefreq = "monthly"


class JobPostingSitemap(PublishableSitemap):
    model = JobPosting
    changefreq = "daily"


class IndustrySitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.6

    def items(self):
        return Industry.objects.filter(show_in_nav=True)


class StaticViewSitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.9

    def items(self):
        return ["home", "about", "contact", "privacy", "terms", "demo", "job_posting_list"]

    def location(self, item):
        return reverse(item)


sitemaps = {
    "static": StaticViewSitemap,
    "services": ServiceSitemap,
    "use-cases": UseCaseSitemap,
    "products": ProductSitemap,
    "technologies": TechnologySitemap,
    "hire-roles": HireRoleSitemap,
    "blog": BlogPostSitemap,
    "case-studies": CaseStudySitemap,
    "handbooks": HandbookSitemap,
    "webinars": WebinarSitemap,
    "careers": JobPostingSitemap,
    "industries": IndustrySitemap,
}
