from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from datetime import datetime, timezone
import logging

from SiPanit.firebase import get_db
from .permissions import IsVendor
from .serializers import VendorEventListSerializer, VendorEventDetailSerializer

logger = logging.getLogger(__name__)


def parse_iso_date(date_str):
    """Parse ISO date string to datetime"""
    if not date_str:
        return None
    try:
        # Handle 'Z' timezone
        if date_str.endswith('Z'):
            date_str = date_str[:-1] + '+00:00'
        return datetime.fromisoformat(date_str)
    except:
        return None


def get_event_status(start_date, end_date):
    """Determine event status based on dates"""
    now = datetime.now(timezone.utc)
    start = parse_iso_date(start_date)
    end = parse_iso_date(end_date)
    
    if not start or not end:
        return 'planning'
    
    # Make dates timezone-aware if they aren't
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)
    
    if now < start:
        return 'upcoming'
    elif start <= now <= end:
        return 'active'
    else:
        return 'completed'


class VendorEventViewSet(viewsets.ViewSet):
    """
    ViewSet untuk Vendor - READ ONLY
    Vendor hanya bisa melihat event yang di-assign ke mereka (collaborators)
    """
    permission_classes = [IsAuthenticated, IsVendor]

    def _get_vendor_event_ids(self, user_id):
        """Get all event IDs where user is a collaborator"""
        db = get_db()
        user_id_str = str(user_id)
        
        # Query events where user is in collaborators array
        events_ref = db.collection('events').where(
            'collaborators', 'array_contains', user_id_str
        )
        
        event_ids = [doc.id for doc in events_ref.stream()]
        return event_ids

    def _can_access_event(self, event_doc, user_id):
        """Check if vendor can access this event"""
        collaborators = event_doc.get('collaborators', [])
        return str(user_id) in [str(c) for c in collaborators]

    def list(self, request):
        """
        GET /api/vendor/events/
        List all events assigned to this vendor
        """
        try:
            user_id = request.user.id
            db = get_db()
            
            # Get event IDs where user is collaborator
            event_ids = self._get_vendor_event_ids(user_id)
            
            if not event_ids:
                return Response({'items': []})
            
            # Fetch event details
            events_data = []
            for event_id in event_ids:
                doc = db.collection('events').document(event_id).get()
                if doc.exists:
                    event_dict = doc.to_dict()
                    event_dict['id'] = doc.id
                    
                    # Add computed status
                    event_dict['status'] = get_event_status(
                        event_dict.get('startDate'),
                        event_dict.get('endDate')
                    )
                    
                    events_data.append(event_dict)
            
            # Serialize
            serializer = VendorEventListSerializer(events_data, many=True)
            return Response({'items': serializer.data})
            
        except Exception as e:
            logger.exception("Error listing vendor events")
            return Response(
                {'detail': f'Failed to list events: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def retrieve(self, request, pk=None):
        """
        GET /api/vendor/events/{id}/
        Get detail of a specific event
        """
        try:
            db = get_db()
            doc = db.collection('events').document(pk).get()
            
            if not doc.exists:
                return Response(
                    {'detail': 'Event not found'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            event_dict = doc.to_dict()
            
            # Check access
            if not self._can_access_event(event_dict, request.user.id):
                return Response(
                    {'detail': 'You do not have access to this event'}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            
            event_dict['id'] = doc.id
            event_dict['status'] = get_event_status(
                event_dict.get('startDate'),
                event_dict.get('endDate')
            )
            
            # Serialize
            serializer = VendorEventDetailSerializer(event_dict)
            return Response(serializer.data)
            
        except Exception as e:
            logger.exception(f"Error retrieving event {pk}")
            return Response(
                {'detail': f'Failed to retrieve event: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'], url_path='layout')
    def get_layout(self, request, pk=None):
        """
        GET /api/vendor/events/{id}/layout/
        Get seating layout for event
        """
        try:
            db = get_db()
            
            # Check event exists and user has access
            event_doc = db.collection('events').document(pk).get()
            if not event_doc.exists:
                return Response(
                    {'detail': 'Event not found'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            if not self._can_access_event(event_doc.to_dict(), request.user.id):
                return Response(
                    {'detail': 'You do not have access to this event'}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Get layout
            from event.layout_repository import get_layout as get_layout_fs
            layout = get_layout_fs(pk)
            
            if not layout:
                # Return empty layout structure
                return Response({
                    'event_id': pk,
                    'version': 1,
                    'canvas': {'width': 1200, 'height': 800},
                    'elements': []
                })
            
            return Response(layout)
            
        except Exception as e:
            logger.exception(f"Error getting layout for event {pk}")
            return Response(
                {'detail': f'Failed to get layout: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'], url_path='guests')
    def get_guests(self, request, pk=None):
        """
        GET /api/vendor/events/{id}/guests/
        Get guests list for event
        """
        try:
            db = get_db()
            
            # Check event exists and user has access
            event_doc = db.collection('events').document(pk).get()
            if not event_doc.exists:
                return Response(
                    {'detail': 'Event not found'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            if not self._can_access_event(event_doc.to_dict(), request.user.id):
                return Response(
                    {'detail': 'You do not have access to this event'}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Get guests
            from guest.repository import list_guests
            
            q = request.query_params.get('q')
            tags_any = request.query_params.getlist('tags') or None
            limit = int(request.query_params.get('limit', 50))
            page_token = request.query_params.get('pageToken')
            
            items, next_token = list_guests(
                pk, 
                q=q, 
                tags_any=tags_any, 
                limit=limit, 
                page_token=page_token
            )
            
            return Response({
                'items': items,
                'nextPageToken': next_token
            })
            
        except Exception as e:
            logger.exception(f"Error getting guests for event {pk}")
            return Response(
                {'detail': f'Failed to get guests: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )