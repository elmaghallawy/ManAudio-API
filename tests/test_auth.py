import json
import time
import pytest
from flask import current_app
from app.models import BlacklistToken
from app import db
from app.auth.decorators import get_token_auth_header
from app.auth.errors import AuthError


def register_user(client):
    return client.post(
        '/auth/register',
        data=json.dumps(dict(
            email='joe@gmail.com',
            password='123456'
        )),
        content_type='application/json'
    )


def login_user(client):
    return client.post(
        '/auth/login',
        data=json.dumps(dict(
            email='joe@gmail.com',
            password='123456'
        )),
        content_type='application/json')


def test_get_token_no_header(client):
    """ Test AuthError exception raised
    when there is no Authorization header """
    with current_app.test_request_context():
        with pytest.raises(AuthError) as e:
            assert get_token_auth_header()
            assert e.status_code == 401
            assert e.message == 'Authorization header is expected.'


def test_get_token_no_bearer(client):
    """ Test AuthError exception raised
    when Authorization header is not Bearer"""
    with current_app.test_request_context(headers={'Authorization': ''}):
        with pytest.raises(AuthError) as e:
            assert get_token_auth_header()
            assert e.status_code == 401
            msg = 'Authorization header must start with "Bearer".'
            assert e.message == msg


def test_get_token_no_bearer_token(client):
    """Test AuthError exception raised
    when Authorization header token is comprimised
    """
    with current_app.test_request_context(
            headers={'Authorization': 'Bearer '}):
        with pytest.raises(AuthError) as e:
            assert get_token_auth_header()
            assert e.status_code == 401
            assert e.message == 'Token not found.'


def test_get_token_with_correct_format(client):
    """Test get token from Bearer Authorization header
    when it is correctly formatted
    """
    jwt = 'fsadfenafad'
    bearer_jwt = 'Bearer fsadfenafad'
    with current_app.test_request_context(
            headers={'Authorization': bearer_jwt}):
        token = get_token_auth_header()
        assert token == jwt


def test_registration(client):
    """ Test for user registration """

    response = register_user(client)
    data = json.loads(response.data.decode())
    assert (data['success'])
    assert (data['message'] == 'Successfully registered.')
    assert (data['auth_token'])
    assert (response.content_type == 'application/json')
    assert (response.status_code == 201)


def test_registered_with_already_registered_user(client, user):
    """ Test registration with already registered email"""

    response = register_user(client)
    data = json.loads(response.data.decode())
    assert (not data['success'])
    assert (
        data['message'] == 'User already exists. Please Log in.')
    assert (response.content_type == 'application/json')
    assert (response.status_code == 202)


def test_registered_user_login_correct_password(client, user):
    """Test registered user login"""
    response = login_user(client)
    data = json.loads(response.data.decode())
    assert data['success']
    assert data['message'] == 'Successfully logged in.'
    assert data['auth_token']
    assert response.content_type == 'application/json'
    assert response.status_code == 200


def test_registered_user_login_wrong_password(client, user):
    """Test registered user login"""
    response = client.post(
        '/auth/login',
        data=json.dumps(dict(
            email='joe@gmail.com',
            password='testo'
        )),
        content_type='application/json')
    data = json.loads(response.data.decode())
    assert not data['success']
    assert data['message'] == 'Wrong password.'
    assert not data.get('auth_token')
    assert response.content_type == 'application/json'
    assert response.status_code == 401


def test_non_registered_user_login(client):
    """Test non registered user login"""
    response = login_user(client)
    data = json.loads(response.data.decode())
    assert not data['success']
    assert data['message'] == 'User does not exist.'
    assert not data.get('auth_token')
    assert response.content_type == 'application/json'
    assert response.status_code == 401


def test_user_status(client):
    """Test user status"""
    # register user
    reg_response = register_user(client)
    # get registered user status
    response = client.get(
        '/auth/status',
        headers=dict(
            Authorization='Bearer ' + json.loads(
                reg_response.data.decode()
            )['auth_token']
        )
    )
    data = json.loads(response.data.decode())
    assert data['success']
    assert data['data'] is not None
    assert data['data']['email'] == 'joe@gmail.com'
    assert data['data']['admin'] == 'true' or 'false'
    assert response.status_code == 200


def test_valid_logout(client):
    """Test user logout"""

    # register user
    register_response = register_user(client)
    data = json.loads(register_response.data.decode())
    assert (data['success'])
    assert (data['message'] == 'Successfully registered.')
    assert (data['auth_token'])
    assert (register_response.content_type == 'application/json')
    assert (register_response.status_code == 201)

    # login user
    login_response = login_user(client)
    data = json.loads(login_response.data.decode())
    assert data['success']
    assert data['message'] == 'Successfully logged in.'
    assert data['auth_token']
    assert login_response.content_type == 'application/json'
    assert login_response.status_code == 200

    # logout user

    response = client.post(
        '/auth/logout',
        headers=dict(
            Authorization='Bearer ' + json.loads(
                login_response.data.decode()
            )['auth_token']
        )
    )
    data = json.loads(response.data.decode())
    assert data['success']
    assert data['message'] == 'Successfully logged out.'
    assert response.status_code == 200


def test_invalid_logout(client):
    """Test user logout"""

    # register user
    register_response = register_user(client)
    data = json.loads(register_response.data.decode())
    assert (data['success'])
    assert (data['message'] == 'Successfully registered.')
    assert (data['auth_token'])
    assert (register_response.content_type == 'application/json')
    assert (register_response.status_code == 201)

    # login user
    login_response = login_user(client)
    data = json.loads(login_response.data.decode())
    assert data['success']
    assert data['message'] == 'Successfully logged in.'
    assert data['auth_token']
    assert login_response.content_type == 'application/json'
    assert login_response.status_code == 200

    # sleep 6 secs to make the token expire 'its lifetime is 5 secs'
    time.sleep(6)

    # logout user with invalid token

    response = client.post(
        '/auth/logout',
        headers=dict(
            Authorization='Bearer ' + json.loads(
                login_response.data.decode()
            )['auth_token']
        )
    )
    data = json.loads(response.data.decode())
    assert not data['success']
    assert data['message'] == 'Signature expired, Please login again.'
    assert response.status_code == 401


def test_valid_blacklisted_token_logout(client):
    """ Test for logout after a valid token gets blacklisted """
    # user registration
    resp_register = register_user(client)
    data_register = json.loads(resp_register.data.decode())
    assert data_register['success']
    assert data_register['message'] == 'Successfully registered.'
    assert data_register['auth_token']
    assert resp_register.content_type == 'application/json'
    assert resp_register.status_code == 201
    # user login
    resp_login = login_user(client)
    data_login = json.loads(resp_login.data.decode())
    assert data_login['success']
    assert data_login['message'] == 'Successfully logged in.'
    assert data_login['auth_token']
    assert resp_login.content_type == 'application/json'
    assert resp_login.status_code == 200
    # blacklist a valid token
    blacklist_token = BlacklistToken(
        token=json.loads(resp_login.data.decode())['auth_token'])
    db.session.add(blacklist_token)
    db.session.commit()
    # blacklisted valid token logout
    response = client.post(
        '/auth/logout',
        headers=dict(
            Authorization='Bearer ' + json.loads(
                resp_login.data.decode()
            )['auth_token']
        )
    )
    data = json.loads(response.data.decode())
    assert not data['success']
    assert data['message'] == 'Token blacklisted. Please log in again.'
    assert response.status_code == 401


def test_valid_blacklisted_token_user(client):
    """ Test for user status with a blacklisted valid token """
    resp_register = register_user(client)
    # blacklist a valid token
    blacklist_token = BlacklistToken(
        token=json.loads(resp_register.data.decode())['auth_token'])
    db.session.add(blacklist_token)
    db.session.commit()
    response = client.get(
        '/auth/status',
        headers=dict(
            Authorization='Bearer ' + json.loads(
                resp_register.data.decode()
            )['auth_token']
        )
    )
    data = json.loads(response.data.decode())
    assert not data['success']
    assert data['message'] == 'Token blacklisted. Please log in again.'
    assert response.status_code == 401


def test_headers_success(client):
    # register user
    reg_response = register_user(client)
    # get registered user status
    response = client.get(
        '/auth/headers',
        headers=dict(
            Authorization='Bearer ' + json.loads(
                reg_response.data.decode()
            )['auth_token']
        )
    )
    data = json.loads(response.data.decode())
    assert data['success']
    assert data['message'] == 'Access Granted'
    assert response.status_code == 200


def test_headers_failure(client):
    # register user
    reg_response = register_user(client)
    # sleep 6 secs to make the token expire 'its lifetime is 5 secs'
    time.sleep(6)
    # get registered user status
    response = client.get(
        '/auth/headers',
        headers=dict(
            Authorization='Bearer ' + json.loads(
                reg_response.data.decode()
            )['auth_token']
        )
    )
    data = json.loads(response.data.decode())
    assert not data['success']
    assert data['message'] == 'Signature expired, Please login again.'
    assert response.status_code == 401
