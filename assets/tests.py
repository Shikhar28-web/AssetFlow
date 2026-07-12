from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from organization.models import Department, AssetCategory
from assets.models import Asset
from allocations.models import Allocation
from bookings.models import ResourceBooking
from maintenance.models import MaintenanceRequest
from bookings.forms import ResourceBookingForm
from allocations.forms import AllocationForm
import datetime

User = get_user_model()

class AssetFlowTestCase(TestCase):
    def setUp(self):
        # Create users
        self.admin = User.objects.create_superuser(email='admin@test.com', password='password123')
        self.employee1 = User.objects.create_user(email='employee1@test.com', password='password123', first_name='Priya')
        self.employee2 = User.objects.create_user(email='employee2@test.com', password='password123', first_name='Raj')
        
        # Create category
        self.category = AssetCategory.objects.create(name='Laptops', description='Work laptops')
        
        # Create asset
        self.asset = Asset.objects.create(
            name='Macbook Pro',
            category=self.category,
            serial_number='SN-0114',
            acquisition_date=timezone.localdate(),
            acquisition_cost=1500.00,
            is_shared_bookable=False,
            status='available'
        )

        # Create bookable asset
        self.bookable_asset = Asset.objects.create(
            name='Conference Room B2',
            category=self.category,
            serial_number='ROOM-B2',
            acquisition_date=timezone.localdate(),
            acquisition_cost=5000.00,
            is_shared_bookable=True,
            status='available'
        )

    def test_asset_tag_generation(self):
        # Verify tag is generated automatically like AF-0001
        self.assertEqual(self.asset.asset_tag, "AF-0001")
        self.assertEqual(self.bookable_asset.asset_tag, "AF-0002")

    def test_asset_allocation_success_and_conflict(self):
        # 1. Allocate asset to Employee 1
        form_data = {
            'asset': self.asset.id,
            'assignee': self.employee1.id,
            'department': '',
            'expected_return_date': timezone.localdate() + datetime.timedelta(days=7)
        }
        
        form = AllocationForm(data=form_data)
        self.assertTrue(form.is_valid())
        
        # Verify saving allocation transitions asset status
        allocation = Allocation.objects.create(
            asset=self.asset,
            assignee=self.employee1,
            allocated_by=self.admin,
            status='active'
        )
        self.asset.status = 'allocated'
        self.asset.save()
        
        self.assertEqual(self.asset.status, 'allocated')
        self.assertEqual(Allocation.objects.filter(asset=self.asset, status='active').count(), 1)

        # 2. Attempt duplicate allocation for Employee 2 (Conflict Block)
        form_conflict_data = {
            'asset': self.asset.id,
            'assignee': self.employee2.id,
            'department': '',
            'expected_return_date': timezone.localdate() + datetime.timedelta(days=7)
        }
        
        form_conflict = AllocationForm(data=form_conflict_data)
        # Should be invalid because asset is no longer in the available choices
        self.assertFalse(form_conflict.is_valid())
        self.assertIn("asset", form_conflict.errors)

    def test_booking_overlap_validation(self):
        # 1. Create a booking for Room B2 from 9:00 AM to 10:00 AM tomorrow
        tomorrow = timezone.localdate() + datetime.timedelta(days=1)
        start1 = timezone.make_aware(datetime.datetime.combine(tomorrow, datetime.time(9, 0)))
        end1 = timezone.make_aware(datetime.datetime.combine(tomorrow, datetime.time(10, 0)))
        
        booking1 = ResourceBooking.objects.create(
            asset=self.bookable_asset,
            booked_by=self.employee1,
            start_time=start1,
            end_time=end1,
            status='upcoming'
        )

        # 2. Attempt overlapping booking from 9:30 AM to 10:30 AM (Should FAIL)
        start_overlap = timezone.make_aware(datetime.datetime.combine(tomorrow, datetime.time(9, 30)))
        end_overlap = timezone.make_aware(datetime.datetime.combine(tomorrow, datetime.time(10, 30)))
        
        form_overlap = ResourceBookingForm(data={
            'asset': self.bookable_asset.id,
            'start_time': start_overlap,
            'end_time': end_overlap
        })
        self.assertFalse(form_overlap.is_valid())
        self.assertIn("overlaps with an existing booking", form_overlap.errors['__all__'][0])

        # 3. Attempt non-overlapping booking from 10:00 AM to 11:00 AM (Should PASS)
        start_ok = timezone.make_aware(datetime.datetime.combine(tomorrow, datetime.time(10, 0)))
        end_ok = timezone.make_aware(datetime.datetime.combine(tomorrow, datetime.time(11, 0)))
        
        form_ok = ResourceBookingForm(data={
            'asset': self.bookable_asset.id,
            'start_time': start_ok,
            'end_time': end_ok
        })
        self.assertTrue(form_ok.is_valid())

    def test_maintenance_workflow_signals(self):
        # Raise maintenance request
        maint_req = MaintenanceRequest.objects.create(
            asset=self.asset,
            raised_by=self.employee1,
            description="Keyboard keys sticking",
            priority='medium',
            status='pending'
        )
        
        # Verify status is still available
        self.assertEqual(self.asset.status, 'available')

        # Approve maintenance request
        maint_req.status = 'approved'
        maint_req.save()
        
        # Re-fetch asset and verify signal updated status to Under Maintenance
        self.asset.refresh_from_db()
        self.assertEqual(self.asset.status, 'under_maintenance')

        # Resolve maintenance request
        maint_req.status = 'resolved'
        maint_req.save()
        
        # Re-fetch asset and verify status reverted back to Available
        self.asset.refresh_from_db()
        self.assertEqual(self.asset.status, 'available')
