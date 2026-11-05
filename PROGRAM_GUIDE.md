# DormTogether: a simple guide

DormTogether answers three questions: **What chore should I do? Who is doing the other chores? Is the work shared fairly?**

## Using the app

1. Sign in with a demo account, such as `alex` / `DormDemo2026!`.
2. Open **My availability** and choose the weekdays you can do chores.
3. Open **Chores & ratings** and rate how difficult each chore feels, from 1 to 5.
4. Open **Weekly assignments**, choose a week, and generate assignments.
5. Use that same screen to see everyone's chores and their pending/completed status.
6. Mark your chore complete when you finish it. If you need help, request a delegation; the other resident must accept before the chore becomes theirs.

**Workload statistics** shows everyone's workload. Points measure chore difficulty, not money or a grade.

## Reading the code

Start with these files in this order:

| File | What it does |
| --- | --- |
| `app/main.py` | Starts the web app and serves the main page. |
| `app/api/routes.py` | Receives browser requests, checks who is signed in, and calls the chore logic. |
| `app/services/chores.py` | Decides assignments, completion, transfers, and totals. |
| `app/models/__init__.py` | Defines the records stored in the database. |
| `app/static/app.js` | Displays each screen and sends button/form actions to the server. |
| `app/templates/index.html` | Holds the sign-in form, navigation, and page layout. |

A typical action follows this path:

```text
Click “Mark complete”
  → app.js sends a request
  → routes.py identifies the signed-in resident
  → chores.py checks that the chore belongs to them and marks it complete
  → the database transaction saves the change
  → app.js reloads the screen
```

## How chores are assigned

The `generate()` function has four steps, marked in its comments:

1. Check that every active chore has a rating. Its difficulty points are the average of active residents' ratings.
2. Find or create the selected week. Keep any assignments already made.
3. Calculate each resident's recent average workload and points already assigned this week.
4. Process harder chores first. For each chore, choose an available resident with the smallest **recent average + this week's points**.

For example, Alex has a recent average of 2 points and 3 points planned this week: total 5. Bea has a recent average of 3 and 0 planned: total 3. If both are available, Bea gets the next chore. Then its points are added before choosing someone for the following chore.

Ties go to the resident with fewer chores this week, then the lower resident ID. If nobody is available, the chore stays unassigned and the app shows a message.

## The database in plain language

- **Resident:** a person who can sign in.
- **Chore:** a recurring task, such as cleaning the bathroom.
- **ChoreRating:** one person's difficulty rating for one chore.
- **Availability:** whether a person is available on a weekday.
- **Week:** a Monday–Sunday date range.
- **Assignment:** one chore given to one person for one week.
- **Delegation:** a request for someone else to take an assignment.

An assignment keeps its original resident for history. `responsible()` finds who currently owns the work after any accepted transfer. Only that person can mark it complete.

## Checking changes

Run `python -m pytest -q` using the project's Python environment. The existing tests check assignments, transfers, permissions, and statistics using temporary databases.
