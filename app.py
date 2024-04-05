# WattVision Web App
# Clifton George Samuel
# Jesna Felix
# Felix Ikokwu
# Prepared for Dr. T. Akilan
# ESOF-3675
# Perform search and prediction using SGD regressor (SAV model file)

from datetime import datetime
from bson import Decimal128  # store decimal numbers in MongoDB with precise decimal representation
from flask import Flask, render_template, request, redirect, url_for, flash
#  render an HTML template file and return it to the client
#  access incoming request data, such as form data or JSON
#  redirect the client to a different endpoint.
#  build a URL for a specific function endpoint.
#  send temporary messages to the next request, commonly used for displaying notifications or alerts to the user.
from mongo_connection import get_database  # connect to MongoDB database.
import bcrypt  # hashing passwords
import joblib  # saving and loading trained machine learning models.
import numpy as np  # A fundamental package for scientific computing in Python
import pandas as pd  # open-source library providing high-performance and data analysis tools.

# Initialize the Flask app with a static folder
app = Flask(__name__, static_folder='static')
# Secret key for sessions and for flash messages
app.secret_key = b',\xbcc\xc0|\x10\xb0J\x90#iH\xe3.z,\xdf\xfeV\xc2\x8d\n=D'

# Database setup
db = get_database()  # Connect to the database
# Define the collections from the database
collection = db['User']
collection1 = db['power_consumption']
collection2 = db['environmental_factors']
collection3 = db['time_of_day']
collection4 = db['Zone']


# Define the index route which renders the mainpage
@app.route('/')
def index():
    return render_template("index.html")


# This Flask route, `/register`, manages user registration.
def register():
    if request.method == 'POST':
        existing_user = collection.find_one({'Username': request.form['username']})

        if existing_user is None:
            hashed = bcrypt.hashpw(request.form['password'].encode('utf-8'), bcrypt.gensalt())  # hashes the password
            collection.insert_one({
                'UserId': request.form['userid'],
                'Username': request.form['username'],
                'PasswordHash': hashed,
                'Role': request.form['role']
            })
            return redirect(url_for('index'))
        return 'That username already exists!'

    return render_template('register.html')


# This Flask route, `/login`, manages user login.
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = collection.find_one({'Username': request.form['username']})

        if user and bcrypt.checkpw(request.form['password'].encode('utf-8'), user['PasswordHash']):
            return redirect(url_for('homepage'))  # Login success
        return 'Invalid username/password combination'  # Login failed

    return render_template('login.html')


# This Flask route, `/homepage`, manages the homepage of the GUI
@app.route('/homepage')
def homepage():
    return render_template('homepage.html')


# This Flask route, `/search`, manages the search function
@app.route('/search', methods=['GET', 'POST'])
def search():
    if request.method == 'POST':
        date_time = request.form['datetime']
        zoneid = request.form['zoneid']
        try:
            search_datetime = collection1.Datetime(date_time, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return "Invalid datetime format. Please use YYYY-MM-DD HH:MM:SS"

        # Perform the search
        results = collection1.find({
            "Datetime": search_datetime,
            "ZoneID": zoneid
        }, {"PowerConsumption": 1, "_id": 0})  # including the power consumption field and excluding the id field

        # Convert query results to a list to render in the template
        results_list = list(results)

        # Render a template to display the results
        return render_template('search_results.html', results=results_list)

    return render_template('search.html')


# This Flask route, `/search_results`, manages the search results for the query
@app.route('/search_results', methods=['POST'])
def search_results():
    datetime_input = request.form['datetime']
    zoneid_input = request.form['zoneid']
    # Converting datetime_input to a proper datetime format
    try:
        # Aggregation pipeline to "join" collections on EnvFactorID
        pipeline = [
            {
                '$match': {
                    'Datetime': datetime_input,
                    'ZoneID': zoneid_input
                }
            },
            {
                '$lookup': {
                    'from': 'environmental_factors',
                    'localField': 'EnvFactorID',
                    'foreignField': 'EnvFactorID',
                    'as': 'environmental_data'
                }
            },
            {
                '$unwind': '$environmental_data'
            },
            {
                '$project': {
                    'Datetime': 1,
                    'ZoneID': 1,
                    'PowerConsumption': 1,
                    'Temperature': '$environmental_data.Temperature',
                    'WindSpeed': '$environmental_data.WindSpeed',
                    'Humidity': '$environmental_data.Humidity'
                }
            }
        ]
        results = list(collection1.aggregate(pipeline))

        return render_template('search_results.html', results=results)
    except Exception as e:
        # Log the exception
        return f"An error occurred during the search: {str(e)}"


# This Flask route, `/manage`, handles the insert and delete functions
@app.route('/manage', methods=['GET'])
def manage():
    return render_template('manage.html')


@app.route('/manage_action', methods=['POST'])
def manage_action():
    operation = request.form['operation']
    collection_name = request.form['collection']

    # Mapping of collection names to their corresponding insert view function names
    insert_views = {
        'environmental_factors': 'insert_environmental_factors',
        'time_of_day': 'insert_time_of_day',
        'Zone': 'insert_zone',
        'power_consumption': 'insert_power_consumption',
    }

    # Similarly, map collection names to their corresponding to delete view function names
    delete_views = {
        'environmental_factors': 'delete_environmental_factors',
        'time_of_day': 'delete_time_of_day',
        'Zone': 'delete_zone',
        'power_consumption': 'delete_power_consumption',
    }

    if operation == 'insert':
        # Redirect to the insert function/view for the chosen collection
        view_func_name = insert_views.get(collection_name)
        if view_func_name:
            return redirect(url_for(view_func_name))
    elif operation == 'delete':
        # Redirect to the delete function
        view_func_name = delete_views.get(collection_name)
        if view_func_name:
            return redirect(url_for(view_func_name))

    # If the collection name or operation is not recognized
    flash(f'Operation "{operation}" not recognized or not supported for collection "{collection_name}".')
    return redirect(url_for('manage'))


@app.route('/insert/environmental_factors', methods=['GET', 'POST'])
def insert_environmental_factors():
    if request.method == 'POST':
        try:
            datetime_str = request.form['datetime']
            datetime_obj = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")

            env_factor_id = int(request.form['envfactorid'])
            temperature = float(request.form['temperature'])
            wind_speed = float(request.form['windspeed'])
            humidity = float(request.form['humidity'])

            db.environmental_factors.insert_one({
                "Datetime": datetime_obj,
                "EnvFactorID": env_factor_id,
                "Temperature": Decimal128(str(temperature)),
                "WindSpeed": Decimal128(str(wind_speed)),
                "Humidity": Decimal128(str(humidity))
            })

            flash('Record inserted successfully!')
            return redirect(url_for('insert_environmental_factors'))
        except ValueError as e:
            flash(f"An error occurred: {str(e)}")
            return redirect(url_for('insert_environmental_factors'))

    return render_template('insert_env.html')


@app.route('/insert/time_of_day', methods=['GET', 'POST'])
def insert_time_of_day():
    if request.method == 'POST':
        db.time_of_day.insert_one({
            "description": request.form['description'],
            "id": request.form['id']
        })
        flash('Time of Day record inserted successfully!')
        return redirect(url_for('insert_time_of_day'))

    return render_template('insert_time_of_day.html')


@app.route('/insert/insert_zone', methods=['GET', 'POST'])
def insert_zone():
    if request.method == 'POST':
        location_description = request.form['locationdescription']
        zone_id = request.form['zoneid']
        zone_name = request.form['zonename']

        # Inserting the new zone record into the database
        db.Zone.insert_one({
            "LocationDescription": location_description,
            "ZoneID": zone_id,
            "ZoneName": zone_name
        })

        flash('Zone record inserted successfully!')
        return redirect(url_for('insert_zone'))

    return render_template('insert_zone.html')


@app.route('/insert/insert_power_consumption', methods=['GET', 'POST'])
def insert_power_consumption():
    if request.method == 'POST':
        try:
            datetime_str = request.form['datetime']
            env_factor_id = int(request.form['envfactorid'])
            # Ensuring the power consumption value is correctly formatted as Decimal128
            power_consumption = Decimal128(request.form['powerconsumption'])
            time_of_day = request.form['timeofday']
            zone_id = request.form['zoneid']
            record_id = int(request.form['recordid'])

            db.power_consumption.insert_one({
                "DateTime": datetime_str,  # Storing as a string asd datetime is in string
                "EnvFactorID": env_factor_id,
                "PowerConsumption": power_consumption,
                "TimeOfDay": time_of_day,
                "ZoneID": zone_id,
                "RecordID": record_id
            })

            flash('Power consumption record inserted successfully!')
            return redirect(url_for('insert_power_consumption'))
        except ValueError as e:
            flash(f"An error occurred: {str(e)}")
            return redirect(url_for('insert_power_consumption'))

    return render_template('insert_power_consumption.html')


# Route to handle the deletion operation
@app.route('/delete_zone', methods=['POST'])
def delete_zone():
    zone_id = request.form.get('ZoneID')
    try:
        result = db.collection4.delete_one({"ZoneID": zone_id})
        if result.deleted_count > 0:
            flash('Zone record deleted successfully!')
            return redirect(url_for('delete_zone'))
        else:
            flash('No matching Zone record found.')
            return redirect(url_for('delete_zone'))
    except Exception as e:
        flash('An error occurred while attempting to delete the record.')
        print(f"An error occurred: {e}")  # Log the error to the console for debugging

    return redirect(url_for('confirm_delete_zone'))


# Route to render the deletion confirmation page
@app.route('/confirm_delete_zone/<zone_id>')
def confirm_delete_zone(zone_id):
    return render_template('manage.html', zone_id=zone_id)


@app.route('/delete/delete_time_of_day', methods=['POST'])
def delete_time_of_day():
    time_of_day_id = request.form.get('id')
    try:
        result = db.collection3.delete_one({"id": time_of_day_id})
        if result.deleted_count > 0:
            flash('Time of Day record deleted successfully!')
        else:
            flash('No matching Time of Day record found.')
    except Exception as e:
        flash('An error occurred while attempting to delete the record.')
        print(f"An error occurred: {e}")

    return redirect(url_for('manage'))


# trained model
model_filename = 'sgd_regressor_model (60-40).sav'
sgd_regressor = joblib.load(model_filename)


@app.route('/predict', methods=['GET'])
def predict_form():
    return render_template('predict.html')


@app.route('/predict_power', methods=['POST'])
def predict_power():
    # Retrieving values from the form
    temperature = request.form.get('temperature', type=float, default=np.nan)
    windspeed = request.form.get('windspeed', type=float, default=np.nan)
    humidity = request.form.get('humidity', type=float, default=np.nan)

    # Creating a DataFrame to handle the inputs; NaN values are replaced with 0.0
    df = pd.DataFrame([[temperature, windspeed, humidity]], columns=['temperature', 'windspeed', 'humidity'])
    df.fillna(0.0, inplace=True)
    features = df.to_numpy()  # prepare data for processing with libraries that require input data in NumPy array format

    # Making the prediction using the preloaded model
    predicted_value = sgd_regressor.predict(features)[0]
    prediction_text = f'Predicted Power Consumption: {predicted_value:.2f} kWh'

    # Rendering a template with the prediction result
    return render_template('result.html', prediction=prediction_text)


if __name__ == '__main__':
    app.run(debug=True)
