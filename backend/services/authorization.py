import falcon


def require_admin(req, resp, resource, params):
    user = getattr(
        req.context,
        "user",
        None,
    )

    if not user:
        raise falcon.HTTPUnauthorized(
            title="Authentication required",
            description="Please sign in first.",
        )

    if user["role"] != "admin":
        raise falcon.HTTPForbidden(
            title="Admin access required",
            description=(
                "This action is restricted to administrators."
            ),
        )