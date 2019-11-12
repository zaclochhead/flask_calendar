import os
import time
from datetime import datetime, timedelta
import re
from typing import (cast, Optional)  # noqa: F401
from werkzeug.wrappers import Response

from flask import render_template, request, jsonify, redirect, abort, make_response, current_app, g

from flask_calendar.constants import SESSION_ID
from flask_calendar.gregorian_calendar import GregorianCalendar
from flask_calendar.calendar_data import CalendarData
from flask_calendar.authentication import Authentication
from flask_calendar.app_utils import (previous_month_link, next_month_link, new_session_id, add_session, authenticated,
                                      get_session_username, authorized)


def get_authentication() -> Authentication:
    auth = getattr(g, '_auth', None)
    if auth is None:
        auth = g._auth = Authentication(
            data_folder=current_app.config['USERS_DATA_FOLDER'],
            password_salt=current_app.config['PASSWORD_SALT'],
            failed_login_delay_base=current_app.config['FAILED_LOGIN_DELAY_BASE'],
        )
    return cast(Authentication, auth)



def index_action() -> Response:
    username = 'a_username'#get_session_username(session_id=str(request.cookies.get(SESSION_ID)))
    authentication = get_authentication()
    user_data = authentication.user_data(username)
    return redirect("/{}/".format(user_data["default_calendar"]))


def login_action() -> Response:
    return cast(Response, render_template("login.html"))


def do_login_action() -> Response:
    username = request.form.get("username", "")
    password = request.form.get("password", "")
    authentication = get_authentication()

    if authentication.is_valid(username, password):
        session_id = new_session_id()
        add_session(session_id, username)
        response = make_response(redirect("/"))
        # TODO: other params from http://flask.pocoo.org/docs/0.12/api/#flask.Response.set_cookie
        response.set_cookie(key=SESSION_ID, value=session_id, max_age=2678400)  # 1 month
        return cast(Response, response)
    else:
        return redirect("/login")




def main_calendar_action(calendar_id: str) -> Response:
    current_day, current_month, current_year = GregorianCalendar.current_date()
    year = int(request.args.get("y", current_year))
    year = max(min(year, current_app.config['MAX_YEAR']), current_app.config['MIN_YEAR'])
    month = int(request.args.get("m", current_month))
    month = max(min(month, 12), 1)
    month_name = GregorianCalendar.MONTH_NAMES[month - 1]

    if current_app.config['HIDE_PAST_TASKS']:
        view_past_tasks = False
    else:
        view_past_tasks = request.cookies.get("ViewPastTasks", "1") == "1"

    calendar_data = CalendarData(current_app.config['DATA_FOLDER'])
    try:
        data = calendar_data.load_calendar(calendar_id)
    except FileNotFoundError:
        abort(404)

    tasks = calendar_data.tasks_from_calendar(year, month, data)
    tasks = calendar_data.add_repetitive_tasks_from_calendar(year, month, data, tasks)

    if not view_past_tasks:
        calendar_data.hide_past_tasks(year, month, tasks)

    return cast(Response, render_template(
        "calendar.html",
        calendar_id=calendar_id,
        year=year,
        month=month,
        month_name=month_name,
        current_year=current_year,
        current_month=current_month,
        current_day=current_day,
        month_days=GregorianCalendar.month_days(year, month),
        previous_month_link=previous_month_link(year, month),
        next_month_link=next_month_link(year, month),
        base_url=current_app.config['BASE_URL'],
        tasks=tasks,
        display_view_past_button=current_app.config['SHOW_VIEW_PAST_BUTTON']))




def new_task_action(calendar_id: str, year: int, month: int) -> Response:
    current_day, current_month, current_year = GregorianCalendar.current_date()
    year = max(min(int(year), current_app.config['MAX_YEAR']), current_app.config['MIN_YEAR'])
    month = max(min(int(month), 12), 1)
    month_names = GregorianCalendar.MONTH_NAMES

    if current_month == month and current_year == year:
        day = current_day
    else:
        day = 1
    day = int(request.args.get("day", day))

    task = {
        "date": CalendarData.date_for_frontend(year, month, day),
        "is_all_day": True,
        "repeats": False,
        "details": ""
    }

    return cast(Response, render_template(
        "task.html",
        calendar_id=calendar_id,
        year=year,
        month=month,
        min_year=current_app.config['MIN_YEAR'],
        max_year=current_app.config['MAX_YEAR'],
        month_names=month_names,
        task=task,
        base_url=current_app.config['BASE_URL'],
        editing=False)
    )




def edit_task_action(calendar_id: str, year: int, month: int, day: int, task_id: int) -> Response:
    month_names = GregorianCalendar.MONTH_NAMES
    calendar_data = CalendarData(current_app.config['DATA_FOLDER'])

    repeats = request.args.get("repeats") == "1"
    try:
        if repeats:
            task = calendar_data.repetitive_task_from_calendar(
                calendar_id=calendar_id, year=year, month=month, task_id=int(task_id)
            )
        else:
            task = calendar_data.task_from_calendar(
                calendar_id=calendar_id, year=year, month=month, day=day, task_id=int(task_id)
            )
    except (FileNotFoundError, IndexError):
        abort(404)

    if task["details"] == "&nbsp;":
        task["details"] = ""

    return cast(Response, render_template(
        "task.html",
        calendar_id=calendar_id,
        year=year,
        month=month,
        day=day,
        min_year=current_app.config['MIN_YEAR'],
        max_year=current_app.config['MAX_YEAR'],
        month_names=month_names,
        task=task,
        base_url=current_app.config['BASE_URL'],
        editing=True)
    )




def update_task_action(calendar_id: str, year: str, month: str, day: str, task_id: str) -> Response:
    # Logic is same as save + delete, could refactor but can wait until need to change any save/delete logic
    print("updating task")
    calendar_data = CalendarData(current_app.config['DATA_FOLDER'])
    image_name=''
    image = request.files.get('test', '')
    print(request.files)
    if image:
        print("saving image {}".format(image.filename))
        image_name = image.filename
        image.save(os.path.join(current_app.config['DATA_FOLDER'], image.filename))
    # For creation of "updated" task use only form data
    title = request.form["title"].strip()
    date = request.form.get("date", "")
    end_date_s = request.form.get("end_date", "")
    calendar_dates = []
    if len(date) > 0:
        date_fragments = re.split("-", date)
        year = int(date_fragments[0])  # type: Optional[int]
        month = int(date_fragments[1])  # type: Optional[int]
        day = int(date_fragments[2])  # type: Optional[int]
    else:
        year = month = day = None
    calendar_dates.append({"year": year, "month": month, "day": day})
    print("end_date - {}".format(end_date_s))
    if end_date_s and end_date_s != date:
        start_date = datetime.strptime(date, "%Y-%m-%d")
        end_date = datetime.strptime(end_date_s, "%Y-%m-%d")
        delta = end_date - start_date
        for i in range(delta.days + 1):
            day = start_date + timedelta(days=i)
            year = int(str(day).split("-")[0])
            month = int(str(day).split("-")[1])
            day = int(str(day).split("-")[2].split(" ")[0])
            if i > 0:
            	calendar_dates.append({"year": year, "month": month, "day": day})
            
    print("calendar_dates - {}".format(calendar_dates))

    if len(date) > 0:
        fragments = re.split("-", date)
        updated_year = int(fragments[0])  # type: Optional[int]
        updated_month = int(fragments[1])  # type: Optional[int]
        updated_day = int(fragments[2])  # type: Optional[int]
    else:
        updated_year = updated_month = updated_day = None
    is_all_day = request.form.get("is_all_day", "0") == "1"
    due_time = request.form["due_time"]
    details = request.form["details"].replace("\r", "").replace("\n", "<br>")
    color = request.form["color"]
    has_repetition = request.form.get("repeats", "0") == "1"
    repetition_type = request.form.get("repetition_type", "")
    repetition_subtype = request.form.get("repetition_subtype", "")
    repetition_value = int(request.form["repetition_value"])  # type: int

    id = int(time.time())
    for i in range(0, len(calendar_dates)):
    	calendar_data.create_task(
                                  id = id, 
				  calendar_id=calendar_id,
    	                          year=calendar_dates[i]["year"],
    	                          month=calendar_dates[i]["month"],
                                  start_date = date,
                                  end_date = end_date_s,
    	                          day=calendar_dates[i]["day"],
    	                          title=title,
    	                          is_all_day=is_all_day,
    	                          due_time=due_time,
    	    		          image=image_name,
    	                          details=details,
    	                          color=color,
    	                          has_repetition=has_repetition,
    	                          repetition_type=repetition_type,
    	                          repetition_subtype=repetition_subtype,
    	                          repetition_value=repetition_value)
    # For deletion of old task data use only url data
    calendar_data.delete_task(calendar_id=calendar_id,
                              year_str=year,
                              month_str=month,
                              day_str=day,
                              task_id=int(task_id))

    if updated_year is None:
        return redirect("{}/{}/".format(current_app.config['BASE_URL'], calendar_id), code=302)
    else:
        return redirect("{}/{}/?y={}&m={}".format(
            current_app.config['BASE_URL'], calendar_id, updated_year, updated_month), code=302
        )




def save_task_action(calendar_id: str) -> Response:
    title = request.form["title"].strip()
    image_name=''
    image = request.files.get('test', '')
    if image:
        print("saving image {}".format(image.filename))
        image_name = image.filename
        image.save(os.path.join(current_app.config['IMAGE_PATH'], image.filename))
    date = request.form.get("date", "")
    end_date_s = request.form.get("end_date", "")
    calendar_dates = []
    if len(date) > 0:
        date_fragments = re.split("-", date)
        year = int(date_fragments[0])  # type: Optional[int]
        month = int(date_fragments[1])  # type: Optional[int]
        day = int(date_fragments[2])  # type: Optional[int]
    else:
        year = month = day = None
    calendar_dates.append({"year": year, "month": month, "day": day})
    print("end_date - {}".format(end_date_s))
    if end_date_s and end_date_s != date:
        start_date = datetime.strptime(date, "%Y-%m-%d")
        end_date = datetime.strptime(end_date_s, "%Y-%m-%d")
        delta = end_date - start_date
        for i in range(delta.days + 1):
            day = start_date + timedelta(days=i)
            year = int(str(day).split("-")[0])
            month = int(str(day).split("-")[1])
            day = int(str(day).split("-")[2].split(" ")[0])
            if i > 0:
            	calendar_dates.append({"year": year, "month": month, "day": day})
	    
    print("calendar_dates - {}".format(calendar_dates))
    is_all_day = request.form.get("is_all_day", "0") == "1"
    due_time = request.form["due_time"]
    details = request.form["details"].replace("\r", "").replace("\n", "<br>")
    color = request.form["color"]
    has_repetition = request.form.get("repeats", "0") == "1"
    repetition_type = request.form.get("repetition_type")
    repetition_subtype = request.form.get("repetition_subtype")
    repetition_value = int(request.form["repetition_value"])

    calendar_data = CalendarData(current_app.config['DATA_FOLDER'])
    id = int(time.time())
    for i in range(0, len(calendar_dates)):
    	calendar_data.create_task(
				  id = id, 		
				  calendar_id=calendar_id,
    	                          year=calendar_dates[i]["year"],
    	                          month=calendar_dates[i]["month"],
                                  start_date = date,
                                  end_date = end_date_s,
    	                          day=calendar_dates[i]["day"],
    	                          title=title,
    	                          is_all_day=is_all_day,
    	                          due_time=due_time,
    	    		          image=image_name,
    	                          details=details,
    	                          color=color,
    	                          has_repetition=has_repetition,
    	                          repetition_type=repetition_type,
    	                          repetition_subtype=repetition_subtype,
    	                          repetition_value=repetition_value)

    if year is None:
        return redirect("{}/{}/".format(current_app.config['BASE_URL'], calendar_id), code=302)
    else:
        return redirect("{}/{}/?y={}&m={}".format(current_app.config['BASE_URL'], calendar_id, year, month), code=302)




def delete_task_action(calendar_id: str, year: str, month: str, day: str, task_id: str) -> Response:
    calendar_data = CalendarData(current_app.config['DATA_FOLDER'])
    calendar_data.delete_task(calendar_id=calendar_id,
                              year_str=year,
                              month_str=month,
                              day_str=day,
                              task_id=int(task_id))

    return cast(Response, jsonify({}))




def update_task_day_action(calendar_id: str, year: str, month: str, day: str, task_id: str) -> Response:
    new_day = request.data.decode("utf-8")

    calendar_data = CalendarData(current_app.config['DATA_FOLDER'])
    calendar_data.update_task_day(calendar_id=calendar_id,
                                  year_str=year,
                                  month_str=month,
                                  day_str=day,
                                  task_id=int(task_id),
                                  new_day_str=new_day)

    return cast(Response, jsonify({}))




def hide_repetition_task_instance_action(calendar_id: str, year: str, month: str, day: str, task_id: str) -> Response:
    calendar_data = CalendarData(current_app.config['DATA_FOLDER'])
    calendar_data.hide_repetition_task_instance(calendar_id=calendar_id,
                                                year_str=year,
                                                month_str=month,
                                                day_str=day,
                                                task_id_str=task_id)

    return cast(Response, jsonify({}))
