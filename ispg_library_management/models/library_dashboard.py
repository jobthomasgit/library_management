from odoo import models, fields, api
from datetime import date, timedelta

class LibraryDashboard(models.Model):
    _name = 'library.dashboard'
    _description = 'Library Dashboard'

    @api.model
    def get_dashboard_data(self):
        """Get all dashboard statistics"""
        return {
            'books': self._get_books_stats(),
            'members': self._get_members_stats(),
            'book_moves': self._get_book_moves_stats(),
            'recent_activities': self._get_recent_activities(),
        }

    @api.model
    def _get_books_stats(self):
        """Get books statistics"""
        book_model = self.env['library.book']
        total_books = book_model.search_count([])
        available_books = book_model.search_count([('availability_status', '=', 'available')])
        unavailable_books = book_model.search_count([('availability_status', '=', 'unavailable')])
        
        return {
            'total': total_books,
            'available': available_books,
            'unavailable': unavailable_books,
            'percentage_available': round((available_books / total_books * 100) if total_books > 0 else 0, 1)
        }

    @api.model
    def _get_members_stats(self):
        """Get members statistics"""
        member_model = self.env['res.partner']
        total_members = member_model.search_count([('is_library_member', '=', True)])
        active_members = member_model.search_count([
            ('is_library_member', '=', True),
            ('membership_status', '=', 'active')
        ])
        expired_members = member_model.search_count([
            ('is_library_member', '=', True),
            ('membership_status', '=', 'expired')
        ])
        pending_members = member_model.search_count([
            ('is_library_member', '=', True),
            ('membership_status', '=', 'pending')
        ])
        
        return {
            'total': total_members,
            'active': active_members,
            'expired': expired_members,
            'pending': pending_members,
            'percentage_active': round((active_members / total_members * 100) if total_members > 0 else 0, 1)
        }

    @api.model
    def _get_book_moves_stats(self):
        """Get book moves statistics"""
        move_model = self.env['book.move']
        total_moves = move_model.search_count([])
        draft_moves = move_model.search_count([('state', '=', 'draft')])
        borrowed_moves = move_model.search_count([('state', '=', 'borrowed')])
        returned_moves = move_model.search_count([('state', '=', 'returned')])
        expired_moves = move_model.search_count([('state', '=', 'expired')])
        
        return {
            'total': total_moves,
            'draft': draft_moves,
            'borrowed': borrowed_moves,
            'returned': returned_moves,
            'expired': expired_moves,
        }

    @api.model
    def _get_recent_activities(self):
        """Get recent activities"""
        move_model = self.env['book.move']
        recent_moves = move_model.search([
            ('create_date', '>=', date.today() - timedelta(days=7))
        ], limit=10, order='create_date desc')

        activities = []
        for move in recent_moves:
            activities.append({
                'id': move.id,
                'book_name': move.book_id.name,
                'member_name': move.member_id.name,
                'action': move.state,
                'date': move.create_date.strftime('%Y-%m-%d %H:%M') if move.create_date else '',
                'type': 'book_move'
            })

        return activities

    @api.model
    def get_chart_data(self):
        """Get data for charts"""
        return {
            'books_by_status': self._get_books_chart_data(),
            'members_by_status': self._get_members_chart_data(),
        }

    @api.model
    def _get_books_chart_data(self):
        """Get books chart data"""
        book_model = self.env['library.book']
        available = book_model.search_count([('availability_status', '=', 'available')])
        unavailable = book_model.search_count([('availability_status', '=', 'unavailable')])
        
        return {
            'labels': ['Available', 'Unavailable'],
            'data': [available, unavailable],
            'colors': ['#28a745', '#dc3545']
        }

    @api.model
    def _get_members_chart_data(self):
        """Get members chart data"""
        member_model = self.env['res.partner']
        active = member_model.search_count([
            ('is_library_member', '=', True),
            ('membership_status', '=', 'active')
        ])
        expired = member_model.search_count([
            ('is_library_member', '=', True),
            ('membership_status', '=', 'expired')
        ])
        
        return {
            'labels': ['Active', 'Expired'],
            'data': [active, expired],
            'colors': ['#28a745', '#dc3545', '#ffc107']
        }