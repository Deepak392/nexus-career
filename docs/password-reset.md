# Password recovery

## User workflow

1. From the login page, select **Forgot password?**.
2. Enter the email address associated with the account.
3. The API returns a generic acknowledgement. When the address belongs to an active account with a usable password, Nexus Career emails a one-time reset link.
4. Open the link and choose a new password.
5. After successful validation, return to the login page and sign in using the new password.

## API

| Method and route | Purpose |
|---|---|
| `POST /api/v1/auth/password-reset/` | Request a reset link using `{ "email": "user@example.com" }`. |
| `POST /api/v1/auth/password-reset/confirm/` | Confirm a reset using `{ "uid": "...", "token": "...", "new_password": "..." }`. |

The request endpoint intentionally returns the same response for known and unknown email addresses. This prevents account enumeration. Reset requests are limited to 5 per hour per client IP, and confirmation attempts to 10 per hour per client IP.

Reset tokens are generated with Django's password-reset token generator and the URL-safe encoded user ID. The default validity is 30 minutes (`PASSWORD_RESET_TIMEOUT=1800`). Changing the user's password invalidates the token, so it cannot be reused. Password validation uses the project's configured Django validators. Existing outstanding refresh tokens are blacklisted after a successful reset.

## Local development

The example environment sets:

- `FRONTEND_BASE_URL=http://localhost:5173`
- `EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend`
- `PASSWORD_RESET_TIMEOUT=1800`

Start the services, submit the Forgot password form, then inspect the backend logs for the email content and local reset link:

```powershell
docker compose logs --tail=100 backend
```

Copy the complete `http://localhost:5173/reset-password?uid=...&token=...` link into the browser.

## Production configuration

Before deployment:

- Set `FRONTEND_BASE_URL` to the HTTPS origin serving the frontend.
- Set `EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend`.
- Configure `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS`, and `DEFAULT_FROM_EMAIL` for the organization's trusted email provider.
- Store SMTP credentials in deployment secrets, not in source control.
- Confirm that outbound email delivery and link routing work in the deployed environment.

Email delivery exceptions are recorded in backend logs while the public API retains its generic response.
