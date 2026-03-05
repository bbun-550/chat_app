from app.services.db import create_all


def main() -> None:
    create_all()
    print("PostgreSQL tables created via SQLAlchemy")


if __name__ == "__main__":
    main()
