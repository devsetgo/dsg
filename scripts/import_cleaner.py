from dsg_lib.common_functions.file_functions import open_csv, save_csv, save_json
import datetime
import pytz

# set mood value
def set_mood_value(mood_id):

    # mood_id = 1 is "positive"abs
    # mood_id = 2 is "neutral"
    # mood_id = 3 is "negative"
    # mood_id = 4 is "unknown"
    if mood_id == 1:
        return "positive"
    elif mood_id == 2:
        return "neutral"
    elif mood_id == 3:
        return "negative"
    else:
        return "unknown"


def fix_date_value(date_created, timezone="America/New_York"):
    # ensure date is a valid datetime object
    # examples 2013-08-18 19:48:00, 2017-08-20 21:36:42.000000
    # if date is not valid error is raised
    try:
        new_datetime = datetime.datetime.strptime(date_created, "%Y-%m-%d %H:%M:%S.%f")
    except ValueError:
        try:
            new_datetime = datetime.datetime.strptime(date_created, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            raise ValueError(
                "Incorrect data format, should be YYYY-MM-DD HH:MM:SS or YYYY-MM-DD HH:MM:SS.ffffff"
            )

    # Convert the datetime to the provided timezone
    try:
        tz = pytz.timezone(timezone)
        new_datetime = tz.localize(new_datetime)
    except pytz.exceptions.UnknownTimeZoneError:
        # If the provided timezone is invalid, use America/New_York
        tz = pytz.timezone("America/New_York")
        new_datetime = tz.localize(new_datetime)

    # Convert the datetime to UTC
    new_datetime = new_datetime.astimezone(pytz.UTC)
    return new_datetime

def clean_data(data):
    new_data = []
    headers = ["my_note", "mood", "date_created"]
    new_data.append(headers)
    for d in data:
        new_dict = {
            "my_note": d["my_note"],
            "mood": set_mood_value(d["mood_id"]),
            "date_created": fix_date_value(d["date_created"],d["timezone"]),
        }
        new_data.append(list(new_dict.values()))

    # Sort the data by date_created, from oldest to newest
    new_data[1:] = sorted(new_data[1:], key=lambda x: x[2])

    return new_data

def clean_data_json(data):
    new_data = []
    
    for d in data:
        new_dict = {
            "my_note": d["my_note"],
            "mood": set_mood_value(d["mood_id"]),
            "date_created": fix_date_value(d["date_created"]),
        }
        new_data.append(list(new_dict.values()))
    

    return new_data



def main():
    # Load the data
    data = open_csv(
        "export", delimiter=",", quote_level="minimal", skip_initial_space=False
    )
    # Clean the data
    new_data = clean_data(data)
    print(f"{len(new_data)-1} of {len(data)} have been converted")
    save_csv(data=new_data, file_name="export_cleaned.csv")


if __name__ == "__main__":
    main()
