# Share DormTogether with your group

Use GitHub for the source code, Vercel for the website, and Neon PostgreSQL for shared saved data. Your local `dorm.db` remains local; these instructions create a fresh hosted database.

## 1. Put the project on GitHub

Run these commands in your own terminal (the agent workspace does not allow writing `.git`):

```bash
cd /home/roi/Documents/Projects/DS187
gh auth login -h github.com
git init -b main
git add .gitignore .vercelignore .env.example README.md PROGRAM_GUIDE.md DEPLOYMENT.md DECISIONS.md DS187_Codex_Project_Spec.md VERIFICATION.md app alembic alembic.ini package.json pyproject.toml requirements.txt tests vercel.json
git diff --cached --stat
git commit -m "Prepare DormTogether for shared deployment"
gh repo create dorm-together --private --source=. --remote=origin --push
```

If Git asks for your name/email, configure your own Git identity, then repeat the commit. If the repository name already exists, choose another name rather than overwriting it.

The ignore files exclude databases, environment secrets, virtual environments, and local agent/account directories. Do not upload `dorm.db` or credentials.

## 2. Create the Vercel project and database

1. Sign in at https://vercel.com/new and import the GitHub repository.
2. Select **FastAPI** as the framework and use the repository root. The application entrypoint is already configured as `app.main:app`.
3. Create the project. If the initial deployment fails because environment variables are missing, continue with setup below and redeploy afterward.
4. In the project’s **Storage** section, connect a **Neon PostgreSQL** database through the Marketplace. Choose a suitable free plan if available; no paid plan is required by this project.
5. In project **Settings → Environment Variables**, check/set the production variables:

| Name | Value |
| --- | --- |
| `DATABASE_URL` | Neon PostgreSQL connection string (usually added by the integration); keep its SSL parameters. |
| `SECRET_KEY` | One randomly generated secret, at least 32 characters. Use the same value for every production deployment. |
| `COOKIE_SECURE` | `true` |

Generate the session secret locally:

```bash
python3 -c 'import secrets; print(secrets.token_hex(32))'
```

Paste that value into Vercel, not into source code or chat. Give preview deployments their own database if you enable them.

## 3. Create the hosted tables

In your terminal, activate the environment and install dependencies:

```bash
source .venv312/bin/activate
python -m pip install -r requirements.txt
```

Copy the **direct/unpooled** PostgreSQL connection string from Neon. Run the following block and paste the string at the hidden prompt. The subshell keeps the hosted connection out of subsequent local app runs:

```bash
(
  read -rsp 'Paste the Neon direct connection URL: ' DATABASE_URL
  echo
  export DATABASE_URL
  python -m alembic upgrade head
)
```

Check that the migration succeeds before continuing. No migration runs automatically when someone opens the website.

Optional: to populate a fresh classroom database with the four familiar demo accounts and chore history, run:

```bash
(
  read -rsp 'Paste the same Neon direct connection URL: ' DATABASE_URL
  echo
  export DATABASE_URL
  python -m app.seed
)
```

Demo passwords are public in this project. For a group using its own accounts, skip demo seeding; everyone can register, add shared chores, set availability, and rate them.

## 4. Redeploy and share

Redeploy the production deployment from Vercel. Check `/health`, then open the homepage and create an account (or sign in with a seeded demo account).

Have two people sign in using different accounts. Create/rate chores, save availability, generate assignments, and verify they both see the same schedule and completion updates after refreshing.

Share the production `https://…vercel.app` URL with groupmates. They do not need GitHub or Vercel accounts to use the app unless deployment protection is enabled. Repository collaborators are only necessary for groupmates who will edit code; add them through GitHub Settings → Collaborators.

## Current verification

Local SQLite domain tests pass after these changes. Hosted PostgreSQL migrations, concurrent writes, and the Vercel deployment still need live verification. The coding environment could not install the PostgreSQL driver, authenticate GitHub, or access a browser session, so no hosted deployment has been created here.

## References

- https://vercel.com/docs/frameworks/backend/fastapi
- https://vercel.com/kb/guide/is-sqlite-supported-in-vercel
- https://vercel.com/docs/marketplace-storage
