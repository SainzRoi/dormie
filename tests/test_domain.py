"""Business rules tested against a real temporary SQLite database.

Runs under pytest or python -m unittest tests.test_domain.
"""
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from sqlalchemy import select, func, inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.database import Base, make_engine
from app.models import Resident, Chore, ChoreRating, Week, Availability, Assignment, Delegation
from app.services import chores as svc
from app.services.errors import DomainError

START = date(2026, 11, 9)

class DomainTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.engine = make_engine('sqlite:///' + str(Path(self.tmp.name)/'test.db'))
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.people = [Resident(name=n, username=n.lower(), password_hash='test-only', joined_at=datetime(2026,10,1,tzinfo=timezone.utc)) for n in ['Alex','Bea','Carlo','Dana']]
        self.db.add_all(self.people)
        self.db.flush()
        self.chore = Chore(name='Bathroom', description='', due_weekday=4)
        self.db.add(self.chore)
        self.db.flush()
        for r, score in zip(self.people, [5,4,5,4]):
            self.db.add(ChoreRating(resident_id=r.resident_id, chore_id=self.chore.chore_id, intensity_rating=score))
        for r in self.people:
            self.db.add(Availability(resident_id=r.resident_id, weekday=4, is_available=True))
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()
        self.tmp.cleanup()

    def generate(self, start=START):
        return svc.generate(self.db, start, allow_past=True, as_of=START)

    def assignment(self):
        self.generate()
        return self.db.scalar(select(Assignment).join(Week).where(Week.start_date==START))

    def request(self, a):
        return svc.request_delegation(self.db, a.assignment_id, a.resident_id, self.people[1].resident_id, 'Unexpected commitment')['delegation_id']

    def test_seven_entities_and_availability_has_no_week(self):
        self.assertEqual(len(inspect(self.engine).get_table_names()), 7)
        self.assertNotIn('week_id', Availability.__table__.columns)

    def test_collective_decimal_mean_and_active_ratings(self):
        self.assertEqual(svc.scores(self.db)[self.chore.chore_id], (4.5,4))
        self.people[0].is_active = False
        self.db.flush()
        self.assertAlmostEqual(svc.scores(self.db)[self.chore.chore_id][0], 13/3)

    def test_all_valid_rating_values(self):
        row=self.db.scalar(select(ChoreRating))
        for score in range(1,6):
            row.intensity_rating=score
            self.db.flush()

    def test_rating_range_constraint(self):
        for score in [0,6]:
            with self.assertRaises(IntegrityError), self.db.begin_nested():
                self.db.scalar(select(ChoreRating)).intensity_rating=score
                self.db.flush()

    def test_unique_rating_and_availability(self):
        for obj in [ChoreRating(resident_id=1,chore_id=1,intensity_rating=3),Availability(resident_id=1,weekday=4,is_available=True)]:
            with self.assertRaises(IntegrityError), self.db.begin_nested():
                self.db.add(obj)
                self.db.flush()

    def test_zero_ratings_block_whole_transaction(self):
        self.db.add(Chore(name='Unrated',due_weekday=2))
        self.db.flush()
        with self.assertRaisesRegex(DomainError,'Unrated'):
            self.generate()
        self.assertEqual(self.db.scalar(select(func.count()).select_from(Assignment)),0)

    def test_monday_sunday_validation(self):
        self.assertEqual(svc.validate_week(START),date(2026,11,15))
        with self.assertRaises(DomainError):
            svc.validate_week(START+timedelta(days=1))
        for start,end in [(date(2026,11,10),date(2026,11,16)),(START,date(2026,11,14))]:
            with self.assertRaises(IntegrityError), self.db.begin_nested():
                self.db.add(Week(start_date=start,end_date=end));self.db.flush()

    def test_due_date_and_deterministic_tie(self):
        a=self.assignment()
        self.assertEqual(a.due_date,date(2026,11,12))
        self.assertEqual(a.resident_id,1)
        self.assertIn('Historical average',a.rationale)

    def test_manila_join_date(self):
        self.assertEqual(svc.local_date(datetime(2026,11,8,17,tzinfo=timezone.utc)),START)

    def test_missing_availability_is_unavailable(self):
        self.chore.due_weekday=3
        result=self.generate()
        self.assertEqual(result['assignments'],[])
        self.assertIn('no active resident available',result['warnings'][0])

    def test_explicit_unavailability_excluded(self):
        self.db.scalar(select(Availability).where(Availability.resident_id==1)).is_available=False
        self.assertEqual(self.assignment().resident_id,2)

    def test_no_eligible_retry_generates_missing_only(self):
        for av in self.db.scalars(select(Availability)):
            av.is_available=False
        self.assertEqual(len(self.generate()['warnings']),1)
        self.db.scalar(select(Availability).where(Availability.resident_id==3)).is_available=True
        rows=self.generate()['assignments']
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['resident_id'],3)

    def test_idempotent_generation_snapshot(self):
        a=self.assignment(); original=(a.assignment_id,a.resident_id,a.workload_points,a.rationale)
        for r in self.db.scalars(select(ChoreRating)):
            r.intensity_rating=1
        self.db.flush()
        self.generate()
        self.assertEqual(self.db.scalar(select(func.count()).select_from(Assignment)),1)
        self.assertEqual((a.assignment_id,a.resident_id,a.workload_points,a.rationale),original)

    def test_historical_workload_changes_allocation(self):
        past=START-timedelta(weeks=1)
        self.generate(past)
        self.assertEqual(self.assignment().resident_id,2)
        total,avg=svc.history(self.db, START, self.people[0], as_of=START)
        self.assertEqual(total,4.5)
        self.assertEqual(avg,4.5/4)

    def test_newcomer_eligible_week_denominator(self):
        self.people[0].joined_at=datetime(2026,11,3,tzinfo=timezone.utc)
        self.generate(START-timedelta(weeks=1))
        total,avg=svc.history(self.db,START,self.people[0],as_of=START)
        self.assertEqual((total,avg),(4.5,4.5))

    def test_future_resident_not_eligible(self):
        self.people[0].joined_at=datetime(2026,12,1,tzinfo=timezone.utc)
        self.assertEqual(self.assignment().resident_id,2)

    def test_pending_then_accepted_credit_preserves_original(self):
        a=self.assignment(); did=self.request(a)
        self.assertEqual(svc.responsible(self.db,a),1)
        svc.respond(self.db,did,2,'accepted')
        self.assertEqual(a.resident_id,1)
        self.assertEqual(svc.responsible(self.db,a),2)
        totals=svc.weekly_totals(self.db,START)
        self.assertEqual(totals[1]['original'],4.5)
        self.assertEqual(totals[1]['actual'],0)
        self.assertEqual(totals[2]['actual'],4.5)
        self.assertEqual(totals[2]['completed'],0)
        self.assertEqual(sum(r['actual'] for r in totals.values()),4.5)

    def test_completion_permissions_after_transfer(self):
        a=self.assignment();did=self.request(a)
        with self.assertRaises(DomainError):svc.complete(self.db,a.assignment_id,2)
        svc.respond(self.db,did,2,'accepted')
        with self.assertRaises(DomainError):svc.complete(self.db,a.assignment_id,1)
        svc.complete(self.db,a.assignment_id,2)
        self.assertEqual(a.status,'completed')
        self.assertIsNotNone(a.completed_at)
        self.assertEqual(svc.weekly_totals(self.db,START)[2]['completed'],4.5)

    def test_invalid_substitutes_and_completed_delegation(self):
        a=self.assignment()
        for rid in (1,999):
            with self.assertRaises(DomainError):svc.request_delegation(self.db,a.assignment_id,1,rid,'Reason')
        self.db.scalar(select(Availability).where(Availability.resident_id==2)).is_available=False
        self.db.flush()
        with self.assertRaises(DomainError):self.request(a)
        svc.complete(self.db,a.assignment_id,1)
        with self.assertRaises(DomainError):svc.request_delegation(self.db,a.assignment_id,1,3,'Reason')

    def test_duplicate_active_request_database_constraint(self):
        a=self.assignment();self.request(a)
        with self.assertRaises(DomainError):self.request(a)
        with self.assertRaises(IntegrityError),self.db.begin_nested():
            self.db.add(Delegation(assignment_id=a.assignment_id,substitute_resident_id=3,reason='Duplicate'))
            self.db.flush()

    def test_reject_cancel_history_and_acceptance_final(self):
        a=self.assignment();did=self.request(a)
        svc.respond(self.db,did,2,'rejected')
        next_id=self.request(a);svc.respond(self.db,next_id,1,'cancelled')
        final_id=self.request(a);svc.respond(self.db,final_id,2,'accepted')
        with self.assertRaises(DomainError):svc.respond(self.db,final_id,1,'cancelled')
        with self.assertRaises(DomainError):svc.request_delegation(self.db,a.assignment_id,1,3,'Chain')
        self.assertEqual([d.status for d in self.db.scalars(select(Delegation).order_by(Delegation.delegation_id))],['rejected','cancelled','accepted'])

    def test_recheck_availability_at_acceptance(self):
        a=self.assignment();did=self.request(a)
        self.db.scalar(select(Availability).where(Availability.resident_id==2)).is_available=False
        self.db.flush()
        with self.assertRaises(DomainError):svc.respond(self.db,did,2,'accepted')
        self.assertEqual(svc.responsible(self.db,a),1)

    def test_completion_cancels_pending_request(self):
        a=self.assignment();did=self.request(a)
        svc.complete(self.db,a.assignment_id,1)
        self.assertEqual(self.db.get(Delegation,did).status,'cancelled')

    def test_other_resident_cannot_request_respond_or_complete(self):
        a=self.assignment()
        with self.assertRaises(DomainError):svc.request_delegation(self.db,a.assignment_id,3,2,'No')
        did=self.request(a)
        for action in ['accepted','rejected','cancelled']:
            with self.assertRaises(DomainError):svc.respond(self.db,did,3,action)
        with self.assertRaises(DomainError):svc.complete(self.db,a.assignment_id,3)

    def test_statistics_zero_filling_cumulative_average(self):
        self.generate(START-timedelta(weeks=2))
        a=self.assignment()
        did=svc.request_delegation(self.db,a.assignment_id,a.resident_id,3,'Cover')['delegation_id']
        svc.respond(self.db,did,3,'accepted')
        svc.complete(self.db,a.assignment_id,3)
        stats=svc.statistics(self.db,START)
        rows={r['resident_id']:r for r in stats['residents']}
        self.assertEqual(rows[3]['actual'],4.5)
        self.assertEqual(rows[3]['completed'],4.5)
        self.assertEqual(rows[3]['cumulative']['actual'],4.5)
        self.assertEqual(rows[3]['average'],1.5)
        self.assertEqual(rows[4]['actual'],0)
        self.assertEqual(rows[4]['average'],0)
        self.assertEqual(rows[4]['eligible_weeks'],3)
        self.assertEqual(sum(r['cumulative']['actual'] for r in rows.values()),9)

    def test_week_unique_and_foreign_keys(self):
        self.assignment()
        with self.assertRaises(IntegrityError),self.db.begin_nested():
            self.db.add(Week(start_date=START,end_date=START+timedelta(days=6)));self.db.flush()
        with self.assertRaises(IntegrityError),self.db.begin_nested():
            self.db.add(Availability(resident_id=999,weekday=1,is_available=True));self.db.flush()

    def test_completion_status_consistency(self):
        a=self.assignment()
        with self.assertRaises(IntegrityError),self.db.begin_nested():
            a.status='completed';self.db.flush()

    def test_current_week_fewest_chores_tie_break(self):
        # Exact burden tie: resident 1 has one 4.5-point current chore;
        # resident 2 has historical average 4.5, but zero current chores.
        self.people[1].joined_at=datetime(2026,11,2,tzinfo=timezone.utc)
        past=Week(start_date=START-timedelta(weeks=1),end_date=START-timedelta(days=1))
        target=Week(start_date=START,end_date=START+timedelta(days=6))
        self.db.add_all([past,target]);self.db.flush()
        self.db.add_all([Assignment(resident_id=2,chore_id=1,week_id=past.week_id,due_date=date(2026,11,5),workload_points=4.5),Assignment(resident_id=1,chore_id=1,week_id=target.week_id,due_date=date(2026,11,12),workload_points=4.5)])
        c=Chore(name='Second chore',due_weekday=4);self.db.add(c);self.db.flush()
        self.db.add(ChoreRating(resident_id=1,chore_id=c.chore_id,intensity_rating=2))
        self.people[2].is_active=False;self.people[3].is_active=False
        result=self.generate()
        self.assertEqual(next(a for a in result['assignments'] if a['chore_id']==c.chore_id)['resident_id'],2)



class SeedTests(unittest.TestCase):
    def test_demo_seed_and_delegation_idempotent(self):
        from app.seed import seed, demo_delegation, DEMO_WEEK
        with tempfile.TemporaryDirectory() as tmp:
            engine=make_engine('sqlite:///'+str(Path(tmp)/'demo.db'))
            Base.metadata.create_all(engine)
            with Session(engine) as db:
                seed(db);db.commit()
                before=[(a.assignment_id,a.resident_id,a.workload_points,a.rationale) for a in db.scalars(select(Assignment).order_by(Assignment.assignment_id))]
                seed(db);db.commit()
                self.assertEqual(before,[(a.assignment_id,a.resident_id,a.workload_points,a.rationale) for a in db.scalars(select(Assignment).order_by(Assignment.assignment_id))])
                self.assertEqual(len(before),20)
                self.assertEqual([value[0] for _,value in sorted(svc.scores(db).items())],[2,3,4.5,3.5])
                demo_delegation(db);db.commit()
                demo_delegation(db);db.commit()
                self.assertEqual(db.scalar(select(func.count()).select_from(Delegation)),1)
                self.assertAlmostEqual(sum(row['actual'] for row in svc.weekly_totals(db,DEMO_WEEK).values()),13)
                stats=svc.statistics(db,DEMO_WEEK-timedelta(weeks=4))
                self.assertEqual(sum(r['cumulative']['actual'] for r in stats['residents']),65)
            engine.dispose()

if __name__ == '__main__':
    unittest.main()
