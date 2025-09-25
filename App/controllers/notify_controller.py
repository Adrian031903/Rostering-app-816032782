from ..database import db
from ..models.core import User, Notification

def send_notification(recipient_email: str, message: str, channel: str = "inapp",
                      entity_type: str = None, entity_id: int = None):
    user = User.query.filter_by(email=recipient_email).first()
    if not user: raise ValueError("Recipient not found")
    n = Notification(recipient_id=user.id, channel=channel, message=message,
                     entity_type=entity_type, entity_id=entity_id)
    db.session.add(n); db.session.commit()
    return n
