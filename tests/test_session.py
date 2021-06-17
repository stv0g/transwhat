from transWhat.session import Session


def test_setup_works(mock_backend):
    sess = Session(backend=mock_backend, user="mock@user.com", legacyName="", extra=[])    

