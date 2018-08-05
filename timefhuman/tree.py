class Token:
    pass


class DayToken(Token):

    def __init__(self, month, day, year):
        self.month = month
        self.day = day
        self.year = year

    def __repr__(self):
        return '{}/{}/{}'.format(
            self.month, self.day, self.year)


class TimeToken(Token):

    def __init__(self, hour, time_of_day='am', minute=0):
        """
        >>> TimeToken(3, 'pm')
        3 pm
        >>> TimeToken(3, None)
        3:00
        >>> TimeToken(3)
        3 am
        """
        self.relative_hour = hour
        self.minute = minute
        self.time_of_day = time_of_day

        if time_of_day == 'pm':
            self.hour = self.relative_hour + 12
        else:
            self.hour = self.relative_hour

    def __repr__(self):
        if self.time_of_day is None:
            return '{}:{:02d}'.format(self.hour, self.minute)
        if self.minute == 0:
            return '{} {}'.format(self.relative_hour, self.time_of_day)
        return '{}:{:02d} {}'.format(
            self.relative_hour, self.minute, self.time_of_day)


class DayRangeToken(Token):

    def __init__(self, start_date, end_date):
        self.start_date = start_date
        self.end_date = end_date

    def apply_month(self, month):
        self.start_date.month = month
        self.end_date.month = month

    def apply_year(self, year):
        self.start_date.year = year
        self.end_date.year = year

    def __repr__(self):
        return '{} - {}'.format(repr(self.start_date), repr(self.end_date))


class TimeRangeToken(Token):

    def __init__(self, start_time, end_time):
        self.start_time = start_time
        self.end_time = end_time

    def __repr__(self):
        return '{} - {}'.format(repr(self.start_time), repr(self.end_time))


class AmbiguousToken(Token):

    def __init__(self, *tokens):
        self.tokens = tokens

    def has_time_range_token(self):
        return any([isinstance(token, TimeRangeToken) for token in self.tokens])

    def get_time_range_token(self):
        for token in self.tokens:
            if isinstance(token, TimeRangeToken):
                return token
        return None

    def has_day_range_token(self):
        return any([isinstance(token, DayRangeToken) for token in self.tokens])

    def get_day_range_token(self):
        for token in self.tokens:
            if isinstance(token, DayRangeToken):
                return token
        return None

    def __repr__(self):
        return ' OR '.join(map(repr, self.tokens))