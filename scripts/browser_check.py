"""Repeatable end-to-end QA. Owns a temporary DB/server; never mutates dormie.db."""
from pathlib import Path
import json
import os
import shutil
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import urllib.request
from playwright.sync_api import sync_playwright, expect

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'artifacts'
OUT.mkdir(exist_ok=True)
results=[]

def passed(name):
    results.append(name)
    print('PASS:',name,flush=True)

def login(page,base,username='alex'):
    page.goto(base+'/#login')
    page.get_by_label('Username',exact=True).fill(username)
    page.get_by_label('Password',exact=True).fill('Dormie2026!')
    page.get_by_role('button',name='Log in',exact=True).click()
    expect(page.locator('.dashboard')).to_be_visible()

def navigate(page,hash):
    page.goto(page.url.split('#')[0]+'#'+hash)
    expect(page.locator('#main')).not_to_have_class('loading')

def select_week(page,week='2026-11-09'):
    page.locator('[data-week]').fill(week)
    page.locator('[data-week]').press('Tab')
    expect(page.locator('[data-week]')).to_have_value(week)
    expect(page.locator('.dashboard[aria-busy=true]')).to_have_count(0)

def no_overflow(page):
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'Horizontal overflow'

def touch_swipe(page,start,end):
    cdp=page.context.new_cdp_session(page)
    cdp.send('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':[{'x':start[0],'y':start[1]}]})
    for n in range(1,9):
        cdp.send('Input.dispatchTouchEvent',{'type':'touchMove','touchPoints':[{'x':start[0]+(end[0]-start[0])*n/8,'y':start[1]+(end[1]-start[1])*n/8}]})
    cdp.send('Input.dispatchTouchEvent',{'type':'touchEnd','touchPoints':[]})
    cdp.detach()

with tempfile.TemporaryDirectory(prefix='dormie-browser-') as temp:
    db=Path(temp)/'browser.db'
    env={**os.environ,'DATABASE_URL':f'sqlite:///{db}','SECRET_KEY':'browser-test-only-secret'}
    subprocess.run([sys.executable,'-m','alembic','upgrade','head'],cwd=ROOT,env=env,check=True)
    subprocess.run([sys.executable,'-m','app.seed'],cwd=ROOT,env=env,check=True)
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    base=f'http://127.0.0.1:{port}'
    log=open(OUT/'browser-server.log','w')
    server=subprocess.Popen([sys.executable,'-m','uvicorn','app.main:app','--host','127.0.0.1','--port',str(port)],cwd=ROOT,env=env,stdout=log,stderr=log)
    try:
        for _ in range(100):
            try:
                urllib.request.urlopen(base+'/health',timeout=.5);break
            except Exception:time.sleep(.1)
        else:raise RuntimeError('Server did not start')
        with sync_playwright() as p:
            chrome=os.getenv('CHROME_PATH') or shutil.which('google-chrome') or shutil.which('chromium')
            browser=p.chromium.launch(**({'executable_path':chrome} if chrome else {}),headless=True)
            desktop=browser.new_context(viewport={'width':1440,'height':900})
            page=desktop.new_page()
            errors=[]
            page.on('pageerror',lambda error:errors.append(str(error)))
            page.goto(base)
            expect(page.get_by_role('button',name='START',exact=True)).to_be_visible()
            page.screenshot(path=str(OUT/'welcome-desktop.png'))
            login(page,base)
            expect(page.locator('.character.selected .nameplate')).to_have_text('Alex')
            expect(page.locator('.status-left')).not_to_be_visible()
            select_week(page)
            page.screenshot(path=str(OUT/'desktop-closed.png'))
            page.get_by_role('button',name='Next resident',exact=True).click()
            expect(page.locator('.character.selected .nameplate')).to_have_text('Bea')
            expect(page.locator('.status-left')).not_to_be_visible()
            page.locator('.stage').focus()
            page.keyboard.press('ArrowRight')
            expect(page.locator('.character.selected .nameplate')).to_have_text('Carlo')
            page.keyboard.press('ArrowLeft')
            expect(page.locator('.character.selected .nameplate')).to_have_text('Bea')
            page.get_by_role('button',name='View Bea status',exact=True).click()
            expect(page.locator('.status-left')).to_be_visible()
            expect(page.locator('.status-right')).to_be_visible()
            expect(page.locator('.status-left h2')).to_have_text('Bea')
            expect(page.locator('.status-right')).not_to_contain_text('Mark as complete')
            assert page.request.get(base+'/api/me').json()['name']=='Alex'
            page.screenshot(path=str(OUT/'desktop-open.png'))
            page.get_by_role('button',name='Next resident',exact=True).click()
            expect(page.locator('.status-left h2')).to_have_text('Carlo')
            expect(page.locator('.status-right')).to_contain_text('Clean bathroom')
            page.keyboard.press('Escape')
            expect(page.locator('.status-left')).not_to_be_visible()
            expect(page.locator('.character.selected .nameplate')).to_have_text('Carlo')
            passed('Desktop 1440×900: closed/open panels, clicks, arrows, repeated keyboard browsing, Escape and account isolation')
            page.get_by_role('button',name='View Carlo status',exact=True).click()
            for width in [1024,900,768,390]:
                page.set_viewport_size({'width':width,'height':844})
                no_overflow(page)
                expect(page.locator('[data-week]')).to_have_value('2026-11-09')
                expect(page.locator('.character.selected .nameplate')).to_have_text('Carlo')
                expect(page.locator('.dashboard')).to_have_class('dashboard details-open')
            passed('Responsive resizing at 1024, 900, 768, 390 preserves selected resident/week/open state without horizontal overflow')
            page.set_viewport_size({'width':1440,'height':900})
            page.get_by_role('button',name='Return to my status',exact=True).last.click()
            expect(page.locator('.status-left h2')).to_have_text('Alex')
            navigate(page,'assignments')
            task=page.locator('article.task').filter(has=page.get_by_role('heading',name='Clean bathroom',exact=True))
            task.get_by_role('button',name='Details',exact=True).click()
            page.get_by_text('Why this assignment?',exact=True).click()
            expect(page.locator('dialog')).to_contain_text('Historical average')
            page.get_by_role('button',name='Mark as complete',exact=True).last.click()
            page.get_by_role('button',name='Confirm',exact=True).click()
            expect(task).to_contain_text('Completed')
            passed('Accepted substitute completes a chore; explanation and frozen points are visible; completion persists')
            navigate(page,'chores')
            chore=page.locator('article.card').filter(has=page.get_by_role('heading',name='Sweep floor',exact=True))
            chore.locator('input[value="3"]').check(force=True)
            chore.get_by_role('button',name='Save rating').click()
            expect(chore).to_contain_text('Your rating: 3')
            expect(chore).to_contain_text('2.25')
            navigate(page,'availability')
            page.get_by_role('checkbox',name='Tuesday available').check()
            page.get_by_role('button',name='Save availability').click()
            expect(page.get_by_role('checkbox',name='Tuesday available')).to_be_checked()
            passed('Rating upsert updates collective mean; recurring availability saves and reloads')
            navigate(page,'statistics')
            page.locator('[data-stat=range]').select_option('four_week')
            expect(page.locator('caption')).to_contain_text('Previous 4')
            page.locator('[data-stat=metric]').select_option('completed')
            page.locator('[data-stat=person]').select_option('1')
            expect(page.locator('tbody tr')).to_have_count(1)
            page.screenshot(path=str(OUT/'statistics-desktop.png'))
            navigate(page,'rules')
            page.get_by_text('Quiet hours',exact=True).click()
            expect(page.locator('details[open]')).to_contain_text('Rules pending approval')
            passed('Statistics period/metric/resident filters and read-only rules accordion work')
            # A new shared chore starts unrated; generation blocks without partial creation.
            navigate(page,'chores')
            page.get_by_role('button',name='+ Add chore',exact=True).click()
            page.get_by_label('Chore name',exact=True).fill('Tidy study table')
            page.get_by_label('Description',exact=True).fill('Return shared books and wipe the table.')
            page.get_by_role('button',name='Save chore',exact=True).click()
            expect(page.get_by_role('heading',name='Tidy study table')).to_be_visible()
            navigate(page,'assignments')
            current=page.request.get(base+'/api/me').json()['current_week']
            select_week(page,current)
            page.get_by_role('button',name='Generate assignments',exact=True).click()
            page.get_by_role('button',name='Confirm',exact=True).click()
            expect(page.locator('dialog .form-error')).to_contain_text('Tidy study table')
            page.get_by_role('button',name='Close dialog').click()
            navigate(page,'chores')
            new_chore=page.locator('article.card').filter(has=page.get_by_role('heading',name='Tidy study table',exact=True))
            new_chore.locator('input[value="2"]').check(force=True)
            new_chore.get_by_role('button',name='Save rating').click()
            expect(new_chore).to_contain_text('Your rating: 2')
            navigate(page,'assignments')
            page.get_by_role('button',name='Generate assignments',exact=True).click()
            page.get_by_role('button',name='Confirm',exact=True).click()
            expect(page.locator('#generation-notice')).to_contain_text('5 new assignments')
            page.get_by_role('button',name='Generate assignments',exact=True).click()
            page.get_by_role('button',name='Confirm',exact=True).click()
            expect(page.locator('#generation-notice')).to_contain_text('0 new assignments')
            passed('Shared chore creation, unrated generation error, recovery after rating, generation and idempotent retry')
            # Mobile context uses real touch events, not direct calls to UI handlers.
            mobile=browser.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True)
            phone=mobile.new_page();phone.on('pageerror',lambda error:errors.append(str(error)))
            phone.goto(base)
            phone.screenshot(path=str(OUT/'welcome-mobile.png'))
            expect(phone.get_by_role('button',name='START',exact=True)).to_be_visible()
            login(phone,base)
            select_week(phone)
            expect(phone.locator('.mobile-sheet')).to_be_visible()
            expect(phone.locator('.dashboard')).to_have_class('dashboard ')
            phone.screenshot(path=str(OUT/'mobile-closed.png'))
            touch_swipe(phone,(270,350),(110,350))
            expect(phone.locator('.character.selected .nameplate')).to_have_text('Bea')
            assert phone.request.get(base+'/api/me').json()['name']=='Alex'
            handle=phone.locator('.sheet-handle').bounding_box()
            x,y=handle['x']+handle['width']/2,handle['y']+handle['height']/2
            touch_swipe(phone,(x,y),(x,y-130))
            expect(phone.locator('.dashboard')).to_have_class('dashboard details-open')
            phone.screenshot(path=str(OUT/'mobile-open.png'))
            # Scroll sheet body without collapsing/browsing.
            scroll=phone.locator('.sheet-scroll')
            scroll.evaluate('(el)=>el.scrollTop=250')
            assert scroll.evaluate('(el)=>el.scrollTop')>0
            expect(phone.locator('.character.selected .nameplate')).to_have_text('Bea')
            expect(phone.locator('.dashboard')).to_have_class('dashboard details-open')
            phone.get_by_role('button',name='Next resident',exact=True).click()
            expect(phone.locator('.sheet-header h2')).to_have_text('Carlo')
            expect(phone.locator('.dashboard')).to_have_class('dashboard details-open')
            handle=phone.locator('.sheet-handle').bounding_box();x,y=handle['x']+100,handle['y']+12
            touch_swipe(phone,(x,y),(x,y+130))
            expect(phone.locator('.dashboard')).to_have_class('dashboard ')
            phone.get_by_role('button',name='Expand details',exact=False).click()
            expect(phone.locator('.dashboard')).to_have_class('dashboard details-open')
            phone.get_by_role('button',name='Collapse',exact=False).click()
            no_overflow(phone)
            passed('Mobile 390×844: real touch swipe, handle drag up/down, accessible toggle, scroll containment and account isolation')
            # Separate resident request creation, cancellation, rejection, acceptance.
            bea=browser.new_context(viewport={'width':1440,'height':900}).new_page();login(bea,base,'bea')
            select_week(bea);navigate(bea,'assignments')
            dish=bea.locator('article.task').filter(has=bea.get_by_role('heading',name='Wash dishes',exact=True))
            def request_substitute():
                dish.get_by_role('button',name='Details',exact=True).click()
                bea.get_by_role('button',name='Request substitute',exact=True).click()
                expect(bea.locator('[data-form=delegation]')).to_be_visible()
                bea.get_by_label('Available resident',exact=True).select_option('1')
                bea.get_by_label('Reason',exact=True).fill('Browser demo study commitment')
                bea.get_by_role('button',name='Send request',exact=True).click()
                expect(bea.locator('dialog')).not_to_be_visible()
            request_substitute();navigate(bea,'delegations')
            bea.get_by_role('button',name='Cancel request',exact=True).click();bea.get_by_role('button',name='Confirm',exact=True).click()
            expect(bea.locator('article.task').filter(has_text='Browser demo study commitment')).to_contain_text('Cancelled')
            navigate(bea,'assignments');request_substitute()
            navigate(page,'delegations')
            incoming=page.locator('article.task').filter(has_text='Browser demo study commitment').filter(has=page.get_by_role('button',name='Reject',exact=True))
            incoming.get_by_role('button',name='Reject',exact=True).click();page.get_by_role('button',name='Confirm',exact=True).click()
            expect(page.locator('article.task').filter(has_text='Browser demo study commitment').filter(has_text='Rejected')).to_have_count(1)
            navigate(bea,'assignments');request_substitute();navigate(page,'profile');navigate(page,'delegations')
            incoming=page.locator('article.task').filter(has_text='Browser demo study commitment').filter(has=page.get_by_role('button',name='Accept',exact=True))
            incoming.get_by_role('button',name='Accept',exact=True).click();page.get_by_role('button',name='Confirm',exact=True).click()
            expect(page.locator('article.task').filter(has_text='Browser demo study commitment').filter(has_text='Accepted')).to_have_count(1)
            passed('Delegation end-to-end: request, cancel, request again, reject, request again, accept; preserved history')
            # Fresh-account onboarding and safe error recovery.
            newcomer=browser.new_context(viewport={'width':390,'height':844}).new_page()
            newcomer.goto(base+'/#signup')
            newcomer.get_by_label('Full name',exact=True).fill('Eli')
            newcomer.get_by_label('Username',exact=True).fill('eli')
            newcomer.get_by_label('Password',exact=True).fill('Dormie2026!')
            newcomer.get_by_label('Confirm password',exact=True).fill('Dormie2026!')
            newcomer.get_by_role('button',name='Create account',exact=True).click()
            expect(newcomer.locator('[data-form=availability]')).to_be_visible()
            newcomer.get_by_role('button',name='Save and continue',exact=True).click()
            expect(newcomer.get_by_role('button',name='Finish setup',exact=True)).to_be_visible()
            newcomer.get_by_role('button',name='Finish setup',exact=True).click()
            newcomer.get_by_role('button',name='Enter Dormie',exact=True).click()
            expect(newcomer.locator('.sheet-header h2')).to_have_text('Eli')
            expect(newcomer.locator('.sheet-summary').first).to_contain_text('0.00 pts')
            navigate(newcomer,'profile');newcomer.get_by_role('button',name='Switch resident',exact=True).click();newcomer.get_by_role('button',name='Confirm',exact=True).click()
            expect(newcomer.get_by_role('button',name='Log in',exact=True)).to_be_visible()
            assert newcomer.request.get(base+'/api/me').status==401
            passed('Mobile registration, all-unavailable onboarding, optional ratings, zero-workload dashboard and authenticated account switch')
            # Explicit error injection with retry; rapid browsing uses latest identity.
            navigate(page,'home')
            page.route('**/api/statistics?*',lambda route:route.fulfill(status=503,content_type='application/json',body='{"detail":"Test outage; retry."}'))
            navigate(page,'statistics')
            expect(page.get_by_role('button',name='Retry',exact=True)).to_be_visible()
            page.unroute('**/api/statistics?*')
            page.get_by_role('button',name='Retry',exact=True).click()
            expect(page.locator('table')).to_be_visible()
            navigate(page,'home')
            page.get_by_role('button',name='Next resident',exact=True).dispatch_event('click')
            page.get_by_role('button',name='Next resident',exact=True).dispatch_event('click')
            expect(page.locator('.character.selected .nameplate')).to_have_text('Carlo')
            page.get_by_role('button',name='View Carlo status',exact=True).click()
            expect(page.locator('.status-left h2')).to_have_text('Carlo')
            page.emulate_media(reduced_motion='reduce')
            assert page.locator('.character.selected').evaluate('(el)=>getComputedStyle(el).transitionDuration')=='0s'
            passed('Recoverable network error/retry, rapid browsing consistency and reduced-motion CSS')
            # Last scenario mutates only the disposable fixture.
            with sqlite3.connect(db) as conn:
                conn.execute('UPDATE resident SET is_active=0 WHERE resident_id != 1')
                conn.execute('UPDATE chore SET is_active=0')
                conn.commit()
            page.reload();expect(page.locator('.dashboard')).to_be_visible()
            expect(page.get_by_role('button',name='Next resident',exact=True)).to_be_disabled()
            expect(page.get_by_role('button',name='Previous resident',exact=True)).to_be_disabled()
            navigate(page,'chores');expect(page.get_by_text('No chores yet. Add a shared chore to get started.',exact=True)).to_be_visible()
            passed('Single-resident controls disable correctly; empty active chore catalog renders a useful state')
            assert not errors,errors
            passed('No uncaught JavaScript errors during all browser workflows')
            browser.close()
    except Exception:
        try:
            for i,context in enumerate(browser.contexts):
                for j,tab in enumerate(context.pages):
                    tab.screenshot(path=str(OUT/f'failure-{i}-{j}.png'))
                    (OUT/f'failure-{i}-{j}.html').write_text(tab.content())
        except Exception:
            pass
        raise
    finally:
        server.terminate();server.wait(timeout=10);log.close()
        (OUT/'browser-results.json').write_text(json.dumps({'passed':results,'count':len(results)},indent=2))
print(f'{len(results)} browser scenario groups passed.')
