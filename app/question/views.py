from flask import abort, flash, redirect, render_template, url_for, request
from flask_login import login_required, current_user

from flask_rq import get_queue
from ..email import send_email

from .forms import NewQuestionForm
from . import question
from .. import db
from ..decorators import admin_required
from ..models import Question, Answer, Role

from ..helpers import bool
# All stuff dealing with adding, editing, and removing questions


@question.route('/new-question', methods=['GET', 'POST'])
@login_required
@admin_required
def new_question():
    """Create a new question."""
    form = NewQuestionForm()
    if form.validate_on_submit():
        question = Question(
            content=form.content.data,
            description=form.description.data,
            icon_name=form.icon_name.data,
            short_name=form.short_name.data,
            type=form.type.data,
            free_response=bool(form.free_response.data))
        db.session.add(question)
        db.session.commit()
        flash('Question {} successfully created'.format(question.content),
              'form-success')
    return render_template('question/new_question.html', form=form)


@question.route('/questions')
@login_required
@admin_required
def questions():
    """View all registered users."""
    questions = Question.query.all()
    return render_template('question/questions.html', questions=questions)


@question.route('/<int:question_id>')
@question.route('/<int:question_id>/info')
@login_required
@admin_required
def question_info(question_id):
    """View a question."""
    question = Question.query.filter_by(id=question_id).first()
    if question is None:
        abort(404)
    return render_template('question/manage_question.html', question=question)


@question.route(
    '/<int:question_id>/change-question-details', methods=['GET', 'POST'])
@login_required
@admin_required
def change_question_details(question_id):
    question = Question.query.filter_by(id=question_id).first()
    if question is None:
        abort(404)
    form = NewQuestionForm()
    if form.validate_on_submit():
        question.content = form.content.data
        question.description = form.description.data
        question.type = form.type.data
        question.icon_name = form.icon_name.data
        question.short_name = form.short_name.data
        question.free_response = bool(form.free_response.data)
        db.session.add(question)
        db.session.commit()
        flash('Question successfully edited', 'form-success')
    form.content.data = question.content
    form.type.data = question.type
    form.icon_name.data = question.icon_name
    form.short_name.data = question.short_name
    form.description.data = question.description
    form.free_response.data = str(question.free_response)
    return render_template(
        'question/manage_question.html', question=question, form=form)


@question.route('/<int:question_id>/delete')
@login_required
@admin_required
def delete_question_request(question_id):
    """Request deletion of a question"""
    question = Question.query.filter_by(id=question_id).first()
    if question is None:
        abort(404)
    return render_template('question/manage_question.html', question=question)


@question.route('/<int:question_id>/_delete')
@login_required
@admin_required
def delete_question(question_id):
    """Delete a question."""
    question = Question.query.filter_by(id=question_id).first()
    db.session.delete(question)
    db.session.commit()
    flash('Successfully deleted question %s.' % question.content, 'success')
    return redirect(url_for('question.questions'))


@question.route('/answer/<int:answer_id>/_delete')
@login_required
@admin_required
def delete_answer(answer_id):
    answer = Answer.query.filter_by(id=answer_id).first()
    club = answer.club.id
    db.session.delete(answer)
    db.session.commit()
    flash('Successfully deleted answer', 'success')
    return redirect(url_for('club.club_info', club_id=club))


@question.route('/answer/<int:answer_id>/flag')
@login_required
def flag_answer(answer_id):
    answer = Answer.query.filter_by(id=answer_id).first()
    link = url_for(
            'question.delete_answer', answer_id=answer.id, _external=True)
    for r in Role.query.filter_by(name='Administrator').all():
        for a in r.users:
            get_queue().enqueue(
                    send_email,
                    recipient=a.email,
                    subject='A new answer report was issued by {}'.format(
                        current_user.first_name),
                    template='question/email/flag',
                    answer=answer,
                    link=link)
    flash('Successfully submitted report', 'success')
    return redirect(url_for('club.club_info', club_id=answer.club.id))
