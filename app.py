# For imports/exceptions see: https://github.com/aws/chalice/blob/master/chalice/__init__.py
from chalice import Chalice, BadRequestError, ConflictError, NotFoundError, Response, AuthResponse, ForbiddenError, UnauthorizedError

from botocore.client import ClientError
from models.APIKey import APIKey
from models.User import User
import helpers
# import copy

app = Chalice(app_name='chalice-pynamodb-bootstrap')


# Our health check, for Docker/development purposes, mostly
@app.route('/healthy')
def healthy():
    return {'healthy': True}


# Create an new user object
@app.route('/users', methods=['POST'])
def create_user():
    # Validate not a duplicate
    try:
        user = User.getByIndex('email', app.current_request.json_body['email'])
        raise ConflictError('This email already exists in our system')
    except ClientError as e:
        if "ResourceNotFoundException" not in str(e):
            raise

    # Create the object via helper and return the results to the user with the right HTTP code
    return Response(
        body=User.createFromDict(app.current_request.json_body).to_json_safe(),
        status_code=201
    )


# Login with our email and password (and optionally expire_in_hours which is 24 by default)
@app.route('/login', methods=['POST'])
def login():
    try:
        user = User.getByIndex('email', app.current_request.json_body['email'])
    except:
        # Doing this here simulates the exact time it would take to hash the password to validate it.  This prevents
        # an attack vector knowing when emails are invalid because they would take less long to respond than if they were valid.
        user = User(email="invalid@invalid.com")
        user.set_password("invalid")
        raise UnauthorizedError("These credentials are invalid")
    try:
        if user.verify_password(app.current_request.json_body['password']):
            print("Adding APIKey for {}".format(user.id))
            api_key = APIKey(user_id=user.id)
            if 'expire_in_hours' in app.current_request.json_body:
                api_key.ttl = helpers.getTTLExpiration(app.current_request.json_body['expire_in_hours'])
            api_key.label = "via login"
            api_key.save()
            return api_key.to_json_safe()
    except Exception as e:
        print("An unexpected exception occurred")
        print(e)
        raise UnauthorizedError("These credentials are invalid")


# Authorizer validating API Key, cache for 300 seconds
@app.authorizer(ttl_seconds=300)
def validate_api_key(auth_request):
    try:
        # print("Try to validate auth request...")
        # print(auth_request.method_arn)
        # print(auth_request.token)
        api_key = APIKey.get(auth_request.token)
        user = User.get(api_key.user_id)
        # TODO: Set routes according to permissions
        return AuthResponse(routes=['*'], principal_id=user)
    except Exception as e:
        print("Caught exception during authorizer")
        print(str(e))
        return AuthResponse(routes=[], principal_id='')


# Get an user object
@app.route('/users/{id}', methods=['GET'], authorizer=validate_api_key)
def get_user(id):
    # Validate input id is valid
    try:
        user = User.get(id)
    except:
        raise NotFoundError("This id was not found in our system")

    # Check if it's us we are querying
    if user.id != app.current_request.context['authorizer']['principalId'].id:
        raise ForbiddenError("You do not have permissions to use this")

    return user.to_json_safe()


# Update an user object
@app.route('/users/{id}', methods=['PUT', 'PATCH'], authorizer=validate_api_key)
def update_user(id):
    # Validate input id is valid
    try:
        user = User.get(id)
    except:
        # We should use Forbidden for more security, but we could use NotFound
        raise ForbiddenError("You do not have permissions to use this")
        # raise NotFoundError("This id was not found in our system")

    # Check if it's us we are updating
    if user.id != app.current_request.context['authorizer']['principalId'].id:
        raise ForbiddenError("You do not have permissions to use this")

    # Update attributes
    user.set_attributes(app.current_request.json_body)
    user.save()
    return user.to_json_safe()


# Delete an user object
@app.route('/users/{id}', methods=['DELETE'], authorizer=validate_api_key)
def delete_user(id):
    # Validate input id is valid
    try:
        user = User.get(id)
    except:
        # We should use Forbidden for more security, but we could use NotFound
        raise ForbiddenError("You do not have permissions to use this")
        # raise NotFoundError("This id was not found in our system")

    # Check if it's us we are deleting
    if user.id != app.current_request.context['authorizer']['principalId'].id:
        raise ForbiddenError("You do not have permissions to use this")

    # TODO: Should consider also deleting all (soft) FK'd resources (eg: API Keys)
    print("Preparing to delete user, grabbing all API Keys...")
    for api_key in APIKey.getByField('user_id', user.id, max_results=1000):
        print("Deleting APIKey: {}".format(api_key.id))
        api_key.delete()

    print("Deleting user {}".format(user.id))
    user.delete()
    return Response( body=None, status_code=204 )


# Tells you who you are
@app.route('/whoami', methods=['GET'], authorizer=validate_api_key)
def whoami():
    return app.current_request.context['authorizer']['principalId'].to_json_safe()
