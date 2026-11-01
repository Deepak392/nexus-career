# API conventions (Sprint 1 baseline)

This document records the current route and documentation baseline. Feature owners must
update the generated schema and this contract when they add real endpoints. No product
routes are registered yet.

## Routing and versioning

- Use the `/api/v1/` prefix and trailing slashes.
- Use `PATCH` for partial updates and follow existing route naming.
- OpenAPI schema: `/api/schema/`; Swagger UI: `/api/docs/`; ReDoc: `/api/redoc/`.
- The schema includes only registered implementation routes. Planned endpoints are not
  represented as if they already exist.

## Authentication and permissions

The repository does not yet implement an authentication mechanism or shared permission
classes. The choice of session, JWT, or university SSO needs confirmation from Deepak and
the supervisor. No security scheme is advertised in OpenAPI until the backend contract
is confirmed. Each feature endpoint must document its actual authentication and role or
ownership checks when implemented.

The schema and UI routes are currently available without authentication and contain no
product routes. The team should review documentation visibility before registering
internal or sensitive endpoints in the generated schema.

## Pagination

DRF list views use page-number pagination when they opt into the configured global
pagination class: `page` selects the page and `page_size` requests a page size. The
default is 20 and the maximum is 50. Paginated responses use DRF's `count`, `next`,
`previous`, and `results` fields. An endpoint should be described as paginated only when
its implementation actually uses pagination.

## Responses, errors, and status codes

The shared error envelope has not been agreed. This project does not add a global
exception handler or claim an error response shape. Deepak and the team need to approve
the shared contract before endpoint schemas can document it consistently.

Use status codes where applicable: `200` success, `201` created, `204` success without a
body, `400` malformed or invalid request, `401` unauthenticated, `403` forbidden, `404`
missing or intentionally concealed resource, `409` conflict, `413` oversized payload,
`422` semantic validation error, and `429` rate limited. Endpoint documentation should
list only statuses its implementation can return.

## Documenting a new endpoint

Register the real route beneath `/api/v1/`, use DRF serializers for request and response
schemas, and add `extend_schema` metadata where inference is incomplete. Document
authentication, permissions, parameters, validation, actual response codes, and
pagination behavior. Add or update API tests and run `pytest` plus
`python manage.py spectacular --validate` before opening the PR.
