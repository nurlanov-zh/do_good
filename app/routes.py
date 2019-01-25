from flask import render_template, flash, redirect, url_for, request
from app import my_app, db
from flask_login import current_user, login_user, login_required, logout_user
from app.models import User
from werkzeug.urls import url_parse
from app.forms import RegistrationForm, EditProfileForm, LoginForm
from datetime import datetime
from app.forms import PostForm
from app.models import Post


@my_app.before_request
def before_request():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.utcnow()
        db.session.commit()

@my_app.route('/', methods=['GET', 'POST'])
@my_app.route('/index', methods=['GET', 'POST'])
@login_required
def index():
    form = PostForm()
    if form.validate_on_submit():
        post = Post(body=form.post.data, author=current_user)
        db.session.add(post)
        db.session.commit()
        flash('Ваш запрос опубликован')
        return redirect(url_for('index'))
    page = request.args.get('page', 1, type=int)
    posts = current_user.followed_posts().paginate(
        page, my_app.config['POSTS_PER_PAGE'], False
    )
    next_url = url_for('index', page=posts.next_num) \
        if posts.has_next else None
    prev_url = url_for('index', page=posts.prev_num) \
        if posts.has_prev else None
    return render_template("index.html", form=form,
                           posts=posts.items, next_url=next_url,
                           prev_url=prev_url)


@my_app.route('/login', methods=['GET', 'POST'])
def login():
    if my_app.config['IP_TRACKABLE']:
        if 'X-Forwarded-For' in request.headers:
            remote_addr = request.headers.getlist("X-Forwarded-For")[0].rpartition(' ')[-1]
        else:
            remote_addr = request.remote_addr or 'untrackable'

    if current_user.is_authenticated:
        current_user.set_location(remote_addr)
        db.session.commit()
        return redirect(url_for('index'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None:
            flash(u'Введенное вами имя пользователя не корректно. Проверьте свое имя пользователя и повторите попытку.')
            return redirect(url_for('login'))
        elif not user.check_password(form.password.data):
            flash(u'Неверный пароль. Проверьте свое имя пользователя или пароль и повторите попытку.')
            return redirect(url_for('login'))
        login_user(user, remember=form.remember_me.data)
        user.set_location(remote_addr)
        db.session.commit()

        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('index')
        return redirect(next_page)
    return render_template('login.html', title='Вход', form=form)


@my_app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))


@my_app.route('/register', methods=['GET', 'POST'])
def register():
    if my_app.config['IP_TRACKABLE']:
        if 'X-Forwarded-For' in request.headers:
            remote_addr = request.headers.getlist("X-Forwarded-For")[0].rpartition(' ')[-1]
        else:
            remote_addr = request.remote_addr or 'untrackable'

    if current_user.is_authenticated:
        current_user.set_location(remote_addr)
        db.session.commit()
        return redirect(url_for('index'))

    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        user.set_location(remote_addr)
        db.session.add(user)
        db.session.commit()
        flash('Поздравляем, Вы зарегистрированы!')
        return redirect(url_for('login'))
    return render_template('register.html', title='Регистрация', form=form)


@my_app.route('/user/<username>')
@login_required
def user(username):
    user = User.query.filter_by(username=username).first_or_404()
    page = request.args.get('page', 1, type=int)
    posts = user.posts.order_by(Post.timestamp.desc()).paginate(
        page, my_app.config['POSTS_PER_PAGE'], False)
    next_url = url_for('user', username=user.username, page=posts.next_num) \
        if posts.has_next else None
    prev_url = url_for('user', username=user.username, page=posts.prev_num) \
        if posts.has_prev else None
    return render_template('user.html', user=user, posts=posts.items,
                           next_url=next_url, prev_url=prev_url)


@my_app.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm(current_user.username)
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.about_me = form.about_me.data
        db.session.commit()
        flash('Ваши изменения сохранены.')
        return redirect(url_for('edit_profile'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.about_me.data = current_user.about_me
    return render_template('edit_profile.html', title='Редактировать профиль',
                           form=form)

@my_app.route('/follow/<username>')
@login_required
def follow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('Пользователь {} не найден.'.format(username))
        return redirect(url_for('index'))
    if user == current_user:
        flash('Вы не можете подписаться на себя!')
        return redirect(url_for('user', username=username))
    current_user.follow(user)
    db.session.commit()
    flash('Вы подписаны к {}!'.format(username))
    return redirect(url_for('user', username=username))

@my_app.route('/unfollow/<username>')
@login_required
def unfollow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('Пользователь {} не найден.'.format(username))
        return redirect(url_for('index'))
    if user == current_user:
        flash('Вы не можете отписаться от себя!')
        return redirect(url_for('user', username=username))
    current_user.unfollow(user)
    db.session.commit()
    flash('Вы отписались от {}.'.format(username))
    return redirect(url_for('user', username=username))


@my_app.route('/explore')
@login_required
def explore():
    page = request.args.get('page', 1, type=int)
    posts = Post.query.order_by(Post.timestamp.desc()).paginate(
        page, my_app.config['POSTS_PER_PAGE'], False
    )
    next_url = url_for('explore', page=posts.next_num) \
        if posts.has_next else None
    prev_url = url_for('explore', page=posts.prev_num) \
        if posts.has_prev else None
    return render_template('index.html', title='Запросы', posts=posts.items,
                           next_url=next_url, prev_url=prev_url)
