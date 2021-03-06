from datetime import datetime
from app import my_app, db
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app import login
from hashlib import md5
from app import avatars
import geoip2.database

GeoIPDatabase = r'GeoLite2-City/GeoLite2-City.mmdb'

followers = db.Table('followers',
    db.Column('follower_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('followed_id', db.Integer, db.ForeignKey('user.id'))
)


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    about_me = db.Column(db.String(140))
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    last_login_ip = db.Column(db.String(40))
    current_login_ip = db.Column(db.String(40))
    country_iso_code = db.Column(db.String(128))
    country_name = db.Column(db.String(128))
    subdivisions_name = db.Column(db.String(128))
    subdivisions_iso_code = db.Column(db.String(128))
    city_name = db.Column(db.String(128))
    postal_code = db.Column(db.String(128))
    location_latitude = db.Column(db.String(128))
    location_longitude = db.Column(db.String(128))

    posts = db.relationship('Post', backref='author', lazy='dynamic')

    followed = db.relationship(
        'User', secondary=followers,
        primaryjoin=(followers.c.follower_id == id),
        secondaryjoin=(followers.c.followed_id == id),
        backref=db.backref('followers', lazy='dynamic'), lazy='dynamic')

    def __repr__(self):
        return '<User {}>'.format(self.username)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def avatar(self, size):
        digest = md5(self.email.lower().encode('utf-8')).hexdigest()
        return avatars.gravatar(digest, size=size, default='monsterid')

    def follow(self, user):
        if not self.is_following(user):
            self.followed.append(user)

    def unfollow(self, user):
        if self.is_following(user):
            self.followed.remove(user)

    def is_following(self, user):
        return self.followed.filter(
            followers.c.followed_id == user.id).count() > 0

    def followed_posts(self):
        followed = Post.query.join(
            followers, (followers.c.followed_id == Post.user_id)).filter(
            followers.c.follower_id == self.id)
        own = Post.query.filter_by(user_id=self.id)
        return followed.union(own).order_by(Post.timestamp.desc())

    def set_location(self, remote_addr):
        old_current_ip, new_current_ip = self.current_login_ip, remote_addr

        self.last_login_ip = old_current_ip or new_current_ip
        self.current_login_ip = new_current_ip

        if old_current_ip != new_current_ip:
            reader = geoip2.database.Reader(GeoIPDatabase)
            success = False
            try:
                response = reader.city(new_current_ip)
                success = True
            except:
                success = False
                # print("An exception occurred")

            if success:
                self.country_iso_code = response.country.iso_code
                self.country_name = response.country.name
                self.subdivisions_name = response.subdivisions.most_specific.name
                self.subdivisions_iso_code = response.subdivisions.most_specific.iso_code
                self.city_name = response.city.name
                self.postal_code = response.postal.code
                self.location_latitude = response.location.latitude
                self.location_longitude = response.location.longitude

            reader.close()


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.String(140))
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    def __repr__(self):
        return '<Запрос {}>'.format(self.body)


@login.user_loader
def load_user(id):
    return User.query.get(int(id))
