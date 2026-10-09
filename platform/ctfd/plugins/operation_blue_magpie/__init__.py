from sqlalchemy import event

from CTFd.models import Awards, Users

STARTING_AWARD_NAME = "Starting Hint Balance"
STARTING_AWARD_DESCRIPTION = "One-time 30-point starting credit for challenge hints."
STARTING_POINTS = 30


def _award_starting_points(mapper, connection, user):
    if user.type == "admin":
        return

    connection.execute(
        Awards.__table__.insert().values(
            user_id=user.id,
            name=STARTING_AWARD_NAME,
            description=STARTING_AWARD_DESCRIPTION,
            value=STARTING_POINTS,
        )
    )


def load(app):
    if not event.contains(Users, "after_insert", _award_starting_points):
        event.listen(Users, "after_insert", _award_starting_points)
