import domain.model
import pytest

import datetime

from sqlalchemy.exc import IntegrityError

from domain.model import User, Article, Comment, Tag, make_comment, make_tag_association

article_date = datetime.date(2020, 2, 28)


def insert_user(session, values=None):
    new_name = "Andrew"
    new_password = "1234"

    if values is not None:
        new_name = values[0]
        new_password = values[1]

    session.execute('INSERT INTO users (username, password) VALUES (:username, :password)',
                    {'username': new_name, 'password': new_password})
    row = session.execute('SELECT id from users where username = :username',
                          {'username': new_name}).fetchone()
    return row[0]


def insert_users(session, values):
    for value in values:
        session.execute('INSERT INTO users (username, password) VALUES (:username, :password)',
                        {'username': value[0], 'password': value[1]})
    rows = list(session.execute('SELECT id from users'))
    keys = tuple(row[0] for row in rows)
    return keys


def insert_article(session):
    session.execute(
        'INSERT INTO articles (date, title, first_para, hyperlink, image_hyperlink) VALUES '
        '(:date, "Coronavirus: First case of virus in New Zealand", '
        '"The first case of coronavirus has been confirmed in New Zealand  and authorities are now scrambling to track down people who may have come into contact with the patient.", '
        '"https://www.stuff.co.nz/national/health/119899280/ministry-of-health-gives-latest-update-on-novel-coronavirus", '
        '"https://resources.stuff.co.nz/content/dam/images/1/z/e/3/w/n/image.related.StuffLandscapeSixteenByNine.1240x700.1zduvk.png/1583369866749.jpg")',
        {'date': article_date.isoformat()}
    )
    row = session.execute('SELECT id from articles').fetchone()
    return row[0]


def insert_tags(session):
    session.execute(
        'INSERT INTO tags (name) VALUES ("News"), ("New Zealand")'
    )
    rows = list(session.execute('SELECT id from tags'))
    keys = tuple(row[0] for row in rows)
    return keys


def insert_article_tag_associations(session, article_key, tag_keys):
    stmt = 'INSERT INTO article_tags (article_id, tag_id) VALUES (:article_id, :tag_id)'
    for tag_key in tag_keys:
        session.execute(stmt, {'article_id': article_key, 'tag_id': tag_key})


def insert_commented_article(session):
    article_key = insert_article(session)
    user_key = insert_user(session)

    timestamp_1 = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    timestamp_2 = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    session.execute(
        'INSERT INTO comments (user_id, article_id, comment, timestamp) VALUES '
        '(:user_id, :article_id, "Comment 1", :timestamp_1),'
        '(:user_id, :article_id, "Comment 2", :timestamp_2)',
        {'user_id': user_key, 'article_id': article_key, 'timestamp_1': timestamp_1, 'timestamp_2': timestamp_2}
    )

    row = session.execute('SELECT id from articles').fetchone()
    return row[0]


def make_article():
    article = Article(
        article_date,
        "Coronavirus: First case of virus in New Zealand",
        "The first case of coronavirus has been confirmed in New Zealand  and authorities are now scrambling to track down people who may have come into contact with the patient.",
        "https://www.stuff.co.nz/national/health/119899280/ministry-of-health-gives-latest-update-on-novel-coronavirus",
        "https://resources.stuff.co.nz/content/dam/images/1/z/e/3/w/n/image.related.StuffLandscapeSixteenByNine.1240x700.1zduvk.png/1583369866749.jpg"
    )
    return article


def make_user():
    user = User("Andrew", "111")
    return user


def make_tag():
    tag = Tag("News")
    return tag


def test_loading_of_users(session):
    users = list()
    users.append(("Andrew", "1234"))
    users.append(("Cindy", "1111"))
    insert_users(session, users)

    expected = [
        User("Andrew", "1234"),
        User("Cindy", "999")
    ]
    assert session.query(User).all() == expected


def test_saving_of_users(session):
    user = make_user()
    session.add(user)
    session.commit()

    rows = list(session.execute('SELECT username, password FROM users'))
    assert rows == [("Andrew", "111")]


def test_saving_of_users_with_common_username(session):
    insert_user(session, ("Andrew", "1234"))
    session.commit()

    with pytest.raises(IntegrityError):
        user = User("Andrew", "111")
        session.add(user)
        session.commit()


def test_loading_of_article(session):
    article_key = insert_article(session)
    expected_article = make_article()
    fetched_article = session.query(Article).one()

    assert expected_article == fetched_article
    assert article_key == fetched_article.id


def test_loading_of_tagged_article(session):
    article_key = insert_article(session)
    tag_keys = insert_tags(session)
    insert_article_tag_associations(session, article_key, tag_keys)

    article = session.query(Article).get(article_key)
    tags = [session.query(Tag).get(key) for key in tag_keys]

    for tag in tags:
        assert article.is_tagged_by(tag)
        assert tag.is_applied_to(article)


def test_loading_of_commented_article(session):
    insert_commented_article(session)

    rows = session.query(Article).all()
    article = rows[0]

    assert len(article._comments) == 2

    for comment in article._comments:
        assert comment._article is article


def test_saving_of_comment(session):
    article_key = insert_article(session)
    user_key = insert_user(session, ("Andrew", "1234"))

    rows = session.query(Article).all()
    article = rows[0]
    user = session.query(User).filter(User._username == "Andrew").one()

    # Create a new Comment that is bidirectionally linked with the User and Article.
    comment_text = "Some comment text."
    comment = make_comment(comment_text, user, article)

    # Note: if the bidirectional links between the new Comment and the User and 
    # Article objects hadn't been established in memory, they would exist following 
    # committing the addition of the Comment to the database.
    session.add(comment)
    session.commit()

    rows = list(session.execute('SELECT user_id, article_id, comment FROM comments'))

    assert rows == [(user_key, article_key, comment_text)]


def test_saving_of_article(session):
    article = make_article()
    session.add(article)
    session.commit()

    rows = list(session.execute('SELECT date, title, first_para, hyperlink, image_hyperlink FROM articles'))
    date = article_date.isoformat()
    assert rows == [(date,
                     "Coronavirus: First case of virus in New Zealand",
                     "The first case of coronavirus has been confirmed in New Zealand  and authorities are now scrambling to track down people who may have come into contact with the patient.",
                     "https://www.stuff.co.nz/national/health/119899280/ministry-of-health-gives-latest-update-on-novel-coronavirus",
                     "https://resources.stuff.co.nz/content/dam/images/1/z/e/3/w/n/image.related.StuffLandscapeSixteenByNine.1240x700.1zduvk.png/1583369866749.jpg"
                     )]


def test_saving_tagged_article(session):
    article = make_article()
    tag = make_tag()

    # Establish the bidirectional relationship between the Article and the Tag.
    make_tag_association(article, tag)

    # Persist the Article (and Tag).
    # Note: it doesn't matter whether we add the Tag or the Article. They are connected
    # bidirectionally, so persisting either one will persist the other.
    session.add(article)
    session.commit()

    # Test test_saving_of_article() checks for insertion into the articles table.
    rows = list(session.execute('SELECT id FROM articles'))
    article_key = rows[0][0]

    # Check that the tags table has a new record.
    rows = list(session.execute('SELECT id, name FROM tags'))
    tag_key = rows[0][0]
    assert rows[0][1] == "News"

    # Check that the article_tags table has a new record.
    rows = list(session.execute('SELECT article_id, tag_id from article_tags'))
    article_foreign_key = rows[0][0]
    tag_foreign_key = rows[0][1]

    assert article_key == article_foreign_key
    assert tag_key == tag_foreign_key


def test_save_commented_article(session):
    # Create Article User objects.
    article = make_article()
    user = make_user()

    # Create a new Comment that is bidirectionally linked with the User and Article.
    comment_text = "Some comment text."
    comment = make_comment(comment_text, user, article)

    # Save the new Article.
    session.add(article)
    session.commit()

    # Test test_saving_of_article() checks for insertion into the articles table.
    rows = list(session.execute('SELECT id FROM articles'))
    article_key = rows[0][0]

    # Test test_saving_of_users() checks for insertion into the users table.
    rows = list(session.execute('SELECT id FROM users'))
    user_key = rows[0][0]

    # Check that the comments table has a new record that links to the articles and users
    # tables.
    rows = list(session.execute('SELECT user_id, article_id, comment FROM comments'))
    assert rows == [(user_key, article_key, comment_text)]
