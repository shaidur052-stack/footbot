"""Conversation persistence.

Messages are saved after the answer is produced, so a failed LLM call leaves
no orphaned half-conversation in the database.
"""

import json

from sqlalchemy.orm import Session

from app.models.user import Conversation, Message

# Three exchanges. Enough for the pronoun and language follow-ups people
# actually ask, without pushing food rows out of the context window.
HISTORY_TURNS = 6


def list_conversations(db: Session, user_id: int, limit: int = 50):
    """Newest first, with a preview of the opening message for the sidebar."""
    rows = (db.query(Conversation)
              .filter(Conversation.user_id == user_id)
              .order_by(Conversation.created_at.desc())
              .limit(limit)
              .all())

    out = []
    for c in rows:
        first = c.messages[0].content if c.messages else ""
        out.append({
            "id": c.id,
            "title": c.title,
            "preview": first[:60],
            "message_count": len(c.messages),
            "created_at": c.created_at.isoformat(),
        })
    return out


def get_conversation(db: Session, user_id: int, conv_id: int):
    """Full message list. Returns None if it isn't this user's conversation."""
    c = (db.query(Conversation)
           .filter(Conversation.id == conv_id, Conversation.user_id == user_id)
           .first())
    if c is None:
        return None

    return {
        "id": c.id,
        "title": c.title,
        "messages": [{
            "id": m.id,
            "role": m.role,
            "content": m.content,
            "sources": json.loads(m.sources_json or "[]"),
            "created_at": m.created_at.isoformat(),
        } for m in c.messages],
    }


def recent_turns(db: Session, user_id: int | None, conv_id: int | None,
                 limit: int = HISTORY_TURNS) -> list[dict]:
    """The last few exchanges, oldest first, for follow-up questions.

    Without this, every message is handled in isolation and follow-ups like
    "in bangla", "and the protein?", or "what about the other one?" have no
    referent — the model cannot know what "the other one" was.

    Anonymous users get an empty list: nothing is stored for them, so there
    is no history to carry.
    """
    if user_id is None or conv_id is None:
        return []

    conv = (db.query(Conversation)
              .filter(Conversation.id == conv_id,
                      Conversation.user_id == user_id)
              .first())
    if conv is None:
        return []

    return [{"role": m.role, "content": m.content} for m in conv.messages[-limit:]]


def create_conversation(db: Session, user_id: int, first_message: str) -> Conversation:
    """Title comes from the first question — cheap, and usually descriptive."""
    title = first_message.strip()[:48]
    if len(first_message.strip()) > 48:
        title += "…"

    conv = Conversation(user_id=user_id, title=title or "New chat")
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return conv


def add_message(db: Session, conv_id: int, role: str, content: str,
                sources: list | None = None) -> Message:
    msg = Message(
        conversation_id=conv_id,
        role=role,
        content=content,
        sources_json=json.dumps(sources or [], ensure_ascii=False),
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg


def save_exchange(db: Session, user_id: int | None, conv_id: int | None,
                  question: str, answer: str, sources: list):
    """Persist one question/answer pair, creating the conversation if needed.

    Anonymous users pass user_id=None and nothing is stored — they can still
    chat, they just have no history.
    """
    if user_id is None:
        return None, None

    if conv_id is None:
        conv = create_conversation(db, user_id, question)
        conv_id = conv.id
    else:
        owned = (db.query(Conversation)
                   .filter(Conversation.id == conv_id,
                           Conversation.user_id == user_id)
                   .first())
        if owned is None:            # not theirs, or deleted — start fresh
            conv = create_conversation(db, user_id, question)
            conv_id = conv.id

    add_message(db, conv_id, "user", question)
    bot_msg = add_message(db, conv_id, "assistant", answer, sources)
    return conv_id, bot_msg.id


def delete_conversation(db: Session, user_id: int, conv_id: int) -> bool:
    c = (db.query(Conversation)
           .filter(Conversation.id == conv_id, Conversation.user_id == user_id)
           .first())
    if c is None:
        return False
    db.delete(c)                     # cascade removes messages and feedback
    db.commit()
    return True