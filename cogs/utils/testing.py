import json
import re

import pymysql
import requests

from .misc import load_json, round_properly, num_to_emoji
from .credentials import MYSQL_USER, MYSQL_PW, DDNET_UPLOAD_TOKEN, DDNET_UPLOAD_URL

database = {
    'host': 'localhost',
    'user': MYSQL_USER,
    'password': MYSQL_PW,
    'db': 'DDNet',
    'use_unicode': 'True',
    'charset': 'utf8mb4'
}


def get_criteria():
    return load_json('map_testing/configs/criteria.json')


def get_server_types():
    return load_json('map_testing/configs/server-types.json')


def register_map(name, mapper, channel_id, submission_msg_id):
    con = pymysql.connect(**database)
    try:
        with con.cursor() as cur:
            query = 'INSERT INTO maps(name, mapper, channel_id, submission_msg_id) VALUES(%s, %s, %s, %s);'
            cur.execute(query, (name, json.dumps(mapper), channel_id, submission_msg_id))

        con.commit()

    finally:
        con.close()


def get_ratings(criteria, channel_id, user_id):
    criteria_list = [c for c in criteria]

    con = pymysql.connect(**database)
    try:
        with con.cursor() as cur:
            if isinstance(user_id, int):
                query = 'SELECT {} FROM ratings WHERE channel_id = %s AND user_id = %s;'.format(
                    ', '.join(criteria_list))
                cur.execute(query, (channel_id, user_id))
                ratings = cur.fetchone()

            if isinstance(user_id, list):
                query = 'SELECT {} FROM ratings WHERE channel_id = %s AND user_id IN %s;'.format(
                    ', '.join(criteria_list))
                cur.execute(query, (channel_id, user_id))
                ratings = cur.fetchall()

                ratings = [[r[n] for r in ratings if r[n] is not None] for n in
                           range(len(criteria_list))]  # Group ratings by criterion and filter None values
                rater_count = len(
                    max(ratings, key=len))  # Get number of ratings for the criterion with the most ratings
                ratings = [round_properly(sum(r) / len(r)) if r else None for r in
                           ratings]  # Calculate average criteria scores
                ratings = (ratings, rater_count)

        con.commit()

    finally:
        con.close()

    return ratings


def submit_ratings(submission, channel_id, user_id):
    con = pymysql.connect(**database)
    try:
        with con.cursor() as cur:
            query = 'SELECT * FROM ratings WHERE channel_id = %s AND user_id = %s;'
            cur.execute(query, (channel_id, user_id))

            if cur.rowcount == 0:
                criteria = [s[0] for s in submission]
                ratings = [str(s[1]) for s in submission]
                query = 'INSERT INTO ratings(channel_id, user_id, {}) VALUES(%s, %s, {});'.format(', '.join(criteria),
                                                                                                  ', '.join(ratings))

            if cur.rowcount == 1:
                insert = [f'{s[0]} = {s[1]}' for s in submission]
                query = 'UPDATE ratings SET {} WHERE channel_id = %s AND user_id = %s;'.format(', '.join(insert))

            cur.execute(query, (channel_id, user_id))

        con.commit()

    finally:
        con.close()


def format_submission(criteria, submission):
    output = []
    for s in submission:
        m = re.search(r'([a-zA-Z]+)=([0-9]+)', s)

        if m:
            crit = m.group(1).lower()
            rating = int(m.group(2))

            if crit.lower() in criteria:
                crit_max = criteria[crit]['max']

                if 0 <= rating <= crit_max:
                    output.append((crit, rating))

                else:
                    return f'Rating for **{crit}** has to be between **0** and **{crit_max}**'

            else:
                return f'`{crit}` is not a valid criterion'

        else:
            return f'Wrong format at `{s}` (Correct usage: `<criterion>=<rating>`)'

    return output


def upload_map(name, path):
    headers = {'X-DDNet-Token': DDNET_UPLOAD_TOKEN}
    params = {'map_name': name}
    files = {'file': open(path, 'rb')}
    r = requests.post(DDNET_UPLOAD_URL, data=params, headers=headers, files=files)
    return r.status_code


def update_schedule_process(channel_id, date=None):
    con = pymysql.connect(**database)
    try:
        with con.cursor() as cur:
            if date:
                query = 'UPDATE testing_schedule SET process_at = %s WHERE channel_id = %s;'
                cur.execute(query, (date, channel_id))
            else:
                query = 'UPDATE testing_schedule SET process_at = NULL WHERE channel_id = %s;'
                cur.execute(query, channel_id)

        con.commit()

    finally:
        con.close()


def get_process(date):
    con = pymysql.connect(**database)
    try:
        with con.cursor() as cur:
            query = 'SELECT channel_id FROM testing_schedule WHERE process_at = %s;'
            cur.execute(query, date)
            results = cur.fetchall()

        con.commit()

    finally:
        con.close()

    return [r[0] for r in results]


def update_schedule(pos, channel_id, date=None):
    con = pymysql.connect(**database)
    try:
        with con.cursor() as cur:
            if pos == 'add':
                query = 'INSERT INTO testing_schedule (channel_id, joined_at) VALUES (%s, %s);'
                cur.execute(query, (channel_id, date))
            if pos == 'remove':
                query = 'DELETE FROM testing_schedule WHERE channel_id = %s;'
                cur.execute(query, channel_id)

        con.commit()

    finally:
        con.close()


def get_schedule():
    con = pymysql.connect(**database)
    try:
        with con.cursor() as cur:
            query = 'SELECT channel_id FROM testing_schedule ORDER BY joined_at ASC;'
            cur.execute(query)
            results = cur.fetchall()

        con.commit()

    finally:
        con.close()

    return [r[0] for r in results]


def get_full_schedule():
    con = pymysql.connect(**database)
    try:
        with con.cursor() as cur:
            query = 'SELECT channel_id, joined_at FROM testing_schedule ORDER BY joined_at ASC;'
            cur.execute(query)
            results = cur.fetchall()

        con.commit()

    finally:
        con.close()

    return [(r[0], r[1]) for r in results]


def get_schedule_pos(channel_id):
    return get_schedule().index(channel_id)


def update_ratings_prompt(criteria, ratings, votes, schedule_pos):
    ratings_string = ''
    if votes is not None:
        overall = num_to_emoji(sum(filter(None, ratings)))
        total = sum([m['max'] for m in criteria.values()])

        criteria_sorted = [(c, m['max']) for c, m in criteria.items()]
        ratings = [f'{c[0].capitalize()}: **{r if r else 0}**/{c[1]}' for c, r in zip(criteria_sorted, ratings)]

        votes_string = f'**{votes}** '
        votes_string += 'Vote' if votes == 1 else 'Votes'

        ratings_string = f'{overall}/{total}  |  ' + '  •  '.join(ratings) + f'  —  {votes_string}  '

    schedule_string = ''
    if schedule_pos >= 0:
        schedule_string = f'🗓  Schedule position: **{schedule_pos + 1}** (~{int(schedule_pos / 3)} '
        schedule_string += 'week' if int(schedule_pos / 3) == 1 else 'weeks'
        schedule_string += ' until being prioritized)'

    return f'{ratings_string}{schedule_string}'
