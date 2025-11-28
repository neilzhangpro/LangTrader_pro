from config.settings import Settings
from models.user import User
from sqlmodel import select

if __name__ == "__main__":
    settings = Settings()
    
    #use ORM
    with settings.get_session() as session:
        statement = select(User).where(User.email == "test@example.com")
        result = session.exec(statement).first()
        print(result)

        #Create a new user
        new_user = User(email="test123@example.com", password_hash="123456hash", otp_verified=True)
        session.add(new_user)
        session.commit()