"""
Management command to sync Firebase Authentication users to Django database

Usage:
    python manage.py sync_firebase_users
    python manage.py sync_firebase_users --dry-run
    python manage.py sync_firebase_users --limit 100
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from firebase_admin import auth
from SiPanit.firebase import init_firebase, get_db

User = get_user_model()


class Command(BaseCommand):
    help = 'Sync Firebase Authentication users to Django database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be synced without actually syncing',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=1000,
            help='Maximum number of users to sync (default: 1000)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        limit = options['limit']

        self.stdout.write(self.style.WARNING('=' * 70))
        self.stdout.write(self.style.WARNING('Firebase → Django User Sync'))
        self.stdout.write(self.style.WARNING('=' * 70))
        
        if dry_run:
            self.stdout.write(self.style.NOTICE('🔍 DRY RUN MODE - No changes will be made\n'))

        # Initialize Firebase
        try:
            init_firebase()
            self.stdout.write(self.style.SUCCESS('✓ Firebase initialized\n'))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'⚠️  Firebase may already be initialized: {e}\n'))

        try:
            # Get all Firebase Auth users
            firebase_users = []
            page = auth.list_users()
            
            while page:
                firebase_users.extend(page.users)
                if len(firebase_users) >= limit:
                    firebase_users = firebase_users[:limit]
                    break
                page = page.get_next_page()

            self.stdout.write(f'📊 Found {len(firebase_users)} Firebase Auth users\n')

            created_count = 0
            updated_count = 0
            skipped_count = 0
            error_count = 0

            for fb_user in firebase_users:
                try:
                    email = fb_user.email
                    uid = fb_user.uid
                    display_name = fb_user.display_name or ''
                    
                    if not email:
                        self.stdout.write(
                            self.style.WARNING(f'⚠️  Skipping user {uid} - no email')
                        )
                        skipped_count += 1
                        continue

                    # Parse name
                    first_name = ''
                    last_name = ''
                    if display_name:
                        parts = display_name.split(' ', 1)
                        first_name = parts[0]
                        last_name = parts[1] if len(parts) > 1 else ''

                    # Check if user exists (by email as username for Google users)
                    user = None
                    try:
                        # First try to find by username=email (Google OAuth pattern)
                        user = User.objects.get(username=email)
                    except User.DoesNotExist:
                        try:
                            # Then try by email field
                            user = User.objects.get(email=email)
                        except User.DoesNotExist:
                            pass

                    if user:
                        # Update existing user
                        updated = False
                        if not user.first_name and first_name:
                            user.first_name = first_name
                            updated = True
                        if not user.last_name and last_name:
                            user.last_name = last_name
                            updated = True
                        
                        if updated and not dry_run:
                            user.save()
                            self.stdout.write(
                                self.style.SUCCESS(f'✓ Updated: {email}')
                            )
                            updated_count += 1
                        elif updated:
                            self.stdout.write(
                                self.style.NOTICE(f'🔍 Would update: {email}')
                            )
                            updated_count += 1
                        else:
                            skipped_count += 1
                    else:
                        # Create new user
                        if not dry_run:
                            user = User.objects.create(
                                username=email,  # Use email as username for Google users
                                email=email,
                                first_name=first_name,
                                last_name=last_name,
                                is_active=not fb_user.disabled,
                                role='planner',  # Default role, can be changed later
                            )
                            # Set unusable password since they use Google OAuth
                            user.set_unusable_password()
                            user.save()
                            
                            self.stdout.write(
                                self.style.SUCCESS(f'✓ Created: {email} (role: planner)')
                            )
                        else:
                            self.stdout.write(
                                self.style.NOTICE(f'🔍 Would create: {email}')
                            )
                        created_count += 1

                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'✗ Error processing {fb_user.uid}: {str(e)}')
                    )
                    error_count += 1

            # Summary
            self.stdout.write('\n' + '=' * 70)
            self.stdout.write(self.style.SUCCESS('SYNC SUMMARY'))
            self.stdout.write('=' * 70)
            self.stdout.write(f'✓ Created:  {created_count}')
            self.stdout.write(f'✓ Updated:  {updated_count}')
            self.stdout.write(f'⊘ Skipped:  {skipped_count}')
            self.stdout.write(f'✗ Errors:   {error_count}')
            self.stdout.write('=' * 70)

            if dry_run:
                self.stdout.write(self.style.WARNING('\n⚠️  This was a DRY RUN - no changes were made'))
                self.stdout.write(self.style.NOTICE('Run without --dry-run to apply changes\n'))
            else:
                self.stdout.write(self.style.SUCCESS('\n✓ Sync completed successfully!\n'))

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'\n✗ Fatal error: {str(e)}\n')
            )
            raise
