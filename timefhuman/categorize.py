from .constants import MONTHS
from .constants import DAYS_OF_WEEK
from .tree import DayToken
from .tree import TimeToken
from .tree import DayRangeToken
from .tree import TimeRangeToken
from .tree import AmbiguousToken
from .tree import Token

import datetime


def categorize(tokens, now):
    tokens = list(tokens)
    tokens = convert_day_of_week(tokens, now)
    tokens = convert_time_of_day(tokens)
    tokens = maybe_extract_hour_minute(tokens)
    tokens = maybe_extract_using_date(tokens, now)
    tokens = maybe_extract_using_month(tokens, now)
    tokens = extract_hour_minute_from_remaining(tokens, now)
    return tokens


# TODO: "monday next week"
def convert_day_of_week(tokens, now=datetime.datetime.now()):
    """Convert day-of-week vernacular into date-like string.

    WARNING: assumes that 'upcoming', and (no specification) implies
    the same day. e.g., 'upcoming Monday', and 'Monday' are both
    the same day. However, it assumes that 'next Monday' is the one *after.
    Also assumes that 'last', 'past', and 'previous' are the same.

    >>> now = datetime.datetime(year=2018, month=8, day=4)
    >>> convert_day_of_week(['Monday', 'at', '3'])
    [8/6/2018, 'at', '3']
    >>> convert_day_of_week(['next', 'Monday', 'at', '3'])
    [8/13/2018, 'at', '3']
    >>> convert_day_of_week(['past', 'Monday', 'at', '3'])
    [7/30/2018, 'at', '3']
    """
    tokens = tokens.copy()
    for i in range(7):
        day = now + datetime.timedelta(i)
        day_of_week = DAYS_OF_WEEK[day.weekday()]

        for string in (day_of_week, day_of_week[:3], day_of_week[:2]):
            if string in tokens:
                index = tokens.index(string)
                new_index, tokens, weeks = extract_weeks_offset(tokens, end=index)
                day = now + datetime.timedelta(weeks*7 + i)
                tokens[new_index] = DayToken(day.month, day.day, day.year)
                break
    return tokens


def extract_weeks_offset(tokens, end=None, key_tokens=(
        'next', 'previous', 'last', 'upcoming', 'past', 'prev')):
    """Extract the number of week offsets needed.

    >>> extract_weeks_offset(['next', 'next', 'week'])
    (0, ['week'], 2)
    >>> extract_weeks_offset(['upcoming', 'Monday'])
    (0, ['Monday'], 0)
    >>> extract_weeks_offset(['last', 'Monday'])
    (0, ['Monday'], -1)
    >>> extract_weeks_offset(['past', 'Tuesday'])
    (0, ['Tuesday'], -1)
    >>> extract_weeks_offset(['past', 'Wed', 'next', 'week'], end=1)
    (0, ['Wed', 'next', 'week'], -1)
    """
    offset = 0
    end = len(tokens) - 1 if end is None else end
    start = end - 1
    if start < 0 or start >= len(tokens):
        return 0, tokens, 0

    while len(tokens) > start >= 0 and \
            tokens[start] in key_tokens:
        candidate = tokens[start]
        if candidate == 'upcoming':
            return start, tokens[:end-1] + tokens[end:], 0
        if candidate == 'next':
            offset += 1
        elif candidate in ('previous', 'prev', 'last', 'past'):
            offset -= 1
        start -= 1
    return start + 1, tokens[:start + 1] + tokens[end:], offset


def convert_time_of_day(tokens):
    """Convert time-of-day vernacular into time-like string.

    >>> convert_time_of_day(['Monday', 'noon', 'huehue'])
    ['Monday', 12 pm, 'huehue']
    >>> convert_time_of_day(['Monday', 'afternoon'])
    ['Monday', 3 pm]
    >>> convert_time_of_day(['Tu', 'evening'])
    ['Tu', 6 pm]
    >>> convert_time_of_day(['Wed', 'morning'])
    ['Wed', 9 am]
    >>> convert_time_of_day(['Thu', 'midnight'])
    ['Thu', 12 am]
    """
    temp_tokens = [token.lower() if isinstance(token, str) else token for token in tokens]
    for keyword, time_tokens in (
            ('morning', [TimeToken(9, 'am')]),
            ('noon', [TimeToken(12, 'pm')]),
            ('afternoon', [TimeToken(3, 'pm')]),
            ('evening', [TimeToken(6, 'pm')]),
            ('night', [TimeToken(9, 'pm')]),
            ('midnight', [TimeToken(12, 'am')])):
        if keyword in temp_tokens:
            index = temp_tokens.index(keyword)
            return tokens[:index] + time_tokens + tokens[index+1:]
    return tokens


def maybe_extract_using_month(tokens, now=datetime.datetime.now()):
    """

    >>> now = datetime.datetime(year=2018, month=7, day=7)
    >>> maybe_extract_using_month(['July', '17', '2018', 'at'])
    [7/17/2018, 'at']
    >>> maybe_extract_using_month(['Jul', '17', 'at'], now=now)
    [7/17/2018, 'at']
    >>> maybe_extract_using_month(['July', 'at'], now=now)
    [7/7/2018, 'at']
    >>> maybe_extract_using_month(['August', '17'], now=now)
    [8/17/2018]
    >>> maybe_extract_using_month(['Aug', 'at'], now=now)
    [8/1/2018, 'at']
    >>> maybe_extract_using_month(['gibberish'], now=now)
    ['gibberish']
    >>> time_range = TimeRangeToken(TimeToken(3, 'pm'), TimeToken(5, 'pm'))
    >>> day_range = DayRangeToken(DayToken(None, 3, None), DayToken(None, 5, None))
    >>> day = DayToken(3, 5, 2018)
    >>> ambiguous_token = AmbiguousToken(time_range, day, day_range)
    >>> maybe_extract_using_month(['May', ambiguous_token])
    [5/3/2018 - 5/5/2018]
    """
    temp_tokens = [token.lower() if isinstance(token, str) else token for token in tokens]
    for mo, month in enumerate(MONTHS, start=1):

        index = None
        month = month.lower()
        if month in temp_tokens:
            index = temp_tokens.index(month)
        if month[:3] in temp_tokens:
            index = temp_tokens.index(month[:3])

        if index is None:
            continue

        next_candidate = tokens[index+1]
        day = 1 if now.month != mo else now.day
        if isinstance(next_candidate, AmbiguousToken):
            if next_candidate.has_day_range_token():
                day_range = next_candidate.get_day_range_token()
                day_range.apply_month(mo)
                day_range.apply_year(now.year)  # TODO: fails on July 3-5, 2018
                return tokens[:index] + [day_range] + tokens[index+2:]
        if not next_candidate.isnumeric():
            day = DayToken(month=mo, day=day, year=now.year)
            return tokens[:index] + [day] + tokens[index+1:]

        next_candidate = int(next_candidate)
        next_next_candidate = tokens[index+2] if len(tokens) > index+2 else ''
        if next_candidate > 31:
            day = 1 if now.month != mo else now.day
            day = DayToken(month=mo, day=day, year=next_candidate)
            return tokens[:index] + [day] + tokens[index+2:]
        elif not next_next_candidate.isnumeric():
            day = DayToken(month=mo, day=next_candidate, year=now.year)
            return tokens[:index] + [day] + tokens[index+2:]

        next_next_candidate = int(next_next_candidate)
        day = DayToken(month=mo, day=next_candidate, year=next_next_candidate)
        return tokens[:index] + [day] + tokens[index+3:]
    return tokens


def maybe_extract_using_date(tokens, now=datetime.datetime.now()):
    """Attempt to extract dates.

    Look for dates in the form of the following:

    (month)/(day)
    (month).(day)
    (month)-(day)
    (month)/(day)/(year)
    (month).(day).(year)
    (month)-(day)-(year)

    >>> maybe_extract_using_date(['7/17/18'])
    [7/17/2018]
    >>> maybe_extract_using_date(['7-17-18'])
    [7/17/2018]
    >>> maybe_extract_using_date(['3', 'on', '7.17.18'])
    ['3', 'on', 7/17/2018]
    >>> maybe_extract_using_date(['7-25', '3-4', 'pm'])
    [7/25/2018, 3/4/2018 OR 3:00 - 4:00, 'pm']
    >>> maybe_extract_using_date(['7/4', '-', '7/6'])
    [7/4/2018, '-', 7/6/2018]
    """
    for i, token in enumerate(tokens):
        if isinstance(token, Token):
            continue
        for punctuation in ('/', '.', '-'):
            if punctuation == token:  # dash joins other tokens, skip parsing
                continue
            if punctuation in token:
                parts = tuple(map(int, token.split(punctuation)))
                if len(parts) == 2:
                    day = DayToken(month=parts[0], day=parts[1], year=now.year)
                    if punctuation == '-' and parts[1] <= 24:
                        day = AmbiguousToken(
                            day,
                            extract_hour_minute_from_time(token)
                        )
                    tokens = tokens[:i] + [day] + tokens[i+1:]
                    continue

                month, day, year = parts
                if year < 1000:
                    year = year + 2000 if year < 50 else year + 1000
                day = DayToken(month=month, day=day, year=year)
                return tokens[:i] + [day] + tokens[i+1:]
    return tokens


def extract_hour_minute_from_time(string, time_of_day=None):
    """

    >>> extract_hour_minute_from_time('3:00')
    3:00
    >>> extract_hour_minute_from_time('3:00', 'pm')
    3 pm
    >>> extract_hour_minute_from_time('3')
    3:00
    >>> extract_hour_minute_from_time('3:30-4', 'pm')
    3:30 pm - 4 pm
    >>> time_range = TimeRangeToken(TimeToken(3, 'pm'), TimeToken(5, 'pm'))
    >>> day_range = DayRangeToken(DayToken(None, 3, None), DayToken(None, 5, None))
    >>> day = DayToken(3, 5, 2018)
    >>> ambiguous_token = AmbiguousToken(time_range, day, day_range)
    >>> extract_hour_minute_from_time(ambiguous_token)
    3 pm - 5 pm
    >>> extract_hour_minute_from_time(AmbiguousToken(day))
    """
    if isinstance(string, AmbiguousToken):
        if string.has_time_range_token():
            return string.get_time_range_token()
        return None

    if '-' in string:
        times = string.split('-')
        start = extract_hour_minute_from_time(times[0], time_of_day)  # TODO: yuck! return a range
        end = extract_hour_minute_from_time(times[1], time_of_day)
        return TimeRangeToken(start, end)

    parts = string.split(':')
    hour = int(parts[0])
    minute = int(parts[1]) if len(parts) >= 2 else 0
    return TimeToken(hour=hour, minute=minute, time_of_day=time_of_day)


def maybe_extract_hour_minute(tokens):
    """Attempt to extract hour and minute.

    If am and pm are found, grab the hour and minute before it. If colon, use
    that as time.

    >>> maybe_extract_hour_minute(['7/17/18', '3', 'PM'])
    ['7/17/18', 3 pm]
    >>> maybe_extract_hour_minute(['7/17/18', '3:00', 'p.m.'])
    ['7/17/18', 3 pm]
    >>> maybe_extract_hour_minute(['July', '17', '2018', 'at', '3', 'p.m.'])
    ['July', '17', '2018', 'at', 3 pm]
    >>> maybe_extract_hour_minute(['July', '17', '2018', '3', 'p.m.'])
    ['July', '17', '2018', 3 pm]
    >>> maybe_extract_hour_minute(['3', 'PM', 'on', 'July', '17'])
    [3 pm, 'on', 'July', '17']
    >>> maybe_extract_hour_minute(['July', 'at', '3'])
    ['July', 'at', '3']
    >>> maybe_extract_hour_minute(['7/17/18', '15:00'])
    ['7/17/18', 15:00]
    >>> maybe_extract_hour_minute(['7/17/18', TimeToken(3, 'pm')])
    ['7/17/18', 3 pm]
    """
    temp_tokens = [token.replace('.', '').lower() if isinstance(token, str) else token for token in tokens]
    remaining_tokens = tokens

    time = None
    time_of_day = None
    for time_of_day in ('am', 'pm'):
        if time_of_day in temp_tokens:
            index = temp_tokens.index(time_of_day)
            time = temp_tokens[index-1]
            time_token = extract_hour_minute_from_time(time, time_of_day)
            return tokens[:index-1] + [time_token] + tokens[index+1:]

    for token in tokens:
        if isinstance(token, Token):
            continue
        if ':' in token:
            time_token = extract_hour_minute_from_time(token, None)
            tokens = [token if ':' not in token else time_token for token in tokens]
            return tokens

    return tokens


def extract_hour_minute_from_remaining(tokens, now=datetime.datetime.now()):
    """Sketch collector for leftovers integers.

    >>> extract_hour_minute_from_remaining(['gibberish'])
    ['gibberish']
    """
    for i, token in enumerate(tokens):
        if isinstance(token, Token):
            continue
        if token.isnumeric():
            time_token = extract_hour_minute_from_time(token)
            return tokens[:i] + [time_token] + tokens[i+1:]
    return tokens