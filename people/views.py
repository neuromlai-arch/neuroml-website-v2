from django.shortcuts import get_object_or_404, render

from people.models import TeamMember


def team_member_detail(request, slug):
    member = get_object_or_404(TeamMember, slug=slug, show_on_about=True)

    breadcrumbs = [
        {"label": "Home", "url": "/"},
        {"label": "About", "url": "/about/"},
        {"label": member.name, "url": None},
    ]
    return render(
        request,
        "people/team_member_detail.html",
        {
            "object": member,
            "recent_posts": member.blogposts.live()[:3],
            "recent_case_studies": member.casestudys.live()[:3],
            "breadcrumbs": breadcrumbs,
        },
    )
