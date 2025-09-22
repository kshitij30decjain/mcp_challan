import sqlite3
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional


class ChallanDatabase:
    def __init__(self, db_path: str = "challan.db"):
        self.db_path = db_path
        self.init_db()
        self.populate_sample_data()

    def init_db(self):
        """Initialize database with required tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Drop existing tables if they exist (for clean setup)
        cursor.execute('DROP TABLE IF EXISTS challans')
        cursor.execute('DROP TABLE IF EXISTS users')
        cursor.execute('DROP TABLE IF EXISTS devices')

        # Create devices table for reference data
        cursor.execute('''
            CREATE TABLE devices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_type TEXT NOT NULL,
                device_model TEXT NOT NULL,
                category TEXT NOT NULL
            )
        ''')

        # Create users table
        cursor.execute('''
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                role TEXT NOT NULL,
                department TEXT NOT NULL,
                full_name TEXT NOT NULL
            )
        ''')

        # Create challans table
        cursor.execute('''
            CREATE TABLE challans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_type TEXT NOT NULL,
                device_model TEXT NOT NULL,
                serial_number TEXT UNIQUE NOT NULL,
                quantity INTEGER NOT NULL,
                purpose TEXT NOT NULL,
                requested_by TEXT NOT NULL,
                request_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                manager_status TEXT DEFAULT 'pending',
                manager_approval_date TIMESTAMP,
                hod_status TEXT DEFAULT 'pending',
                hod_approval_date TIMESTAMP,
                it_status TEXT DEFAULT 'pending',
                it_approval_date TIMESTAMP,
                final_status TEXT DEFAULT 'pending',
                remarks TEXT,
                FOREIGN KEY (requested_by) REFERENCES users(username)
            )
        ''')

        conn.commit()
        conn.close()

    def populate_sample_data(self):
        """Populate database with sample data"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Sample device data (Samsung devices)
        samsung_devices = [
            # Phones
            ('phone', 'Samsung Galaxy S23 Ultra', 'Flagship'),
            ('phone', 'Samsung Galaxy S23+', 'Premium'),
            ('phone', 'Samsung Galaxy S23', 'Premium'),
            ('phone', 'Samsung Galaxy Z Fold 5', 'Foldable'),
            ('phone', 'Samsung Galaxy Z Flip 5', 'Foldable'),
            ('phone', 'Samsung Galaxy A54', 'Mid-range'),
            ('phone', 'Samsung Galaxy A34', 'Mid-range'),
            ('phone', 'Samsung Galaxy M54', 'Budget'),

            # Tablets
            ('tablet', 'Samsung Galaxy Tab S9 Ultra', 'Flagship Tablet'),
            ('tablet', 'Samsung Galaxy Tab S9+', 'Premium Tablet'),
            ('tablet', 'Samsung Galaxy Tab S9', 'Premium Tablet'),
            ('tablet', 'Samsung Galaxy Tab A8', 'Budget Tablet'),
            ('tablet', 'Samsung Galaxy Tab A7 Lite', 'Entry Tablet'),
            ('tablet', 'Samsung Galaxy Tab Active 4 Pro', 'Rugged Tablet'),
        ]

        cursor.executemany(
            'INSERT INTO devices (device_type, device_model, category) VALUES (?, ?, ?)',
            samsung_devices
        )

        # Sample users with different roles
        users = [
            # Managers
            ('john_manager', 'password123', 'manager', 'Operations', 'John Manager'),
            ('sara_director', 'password123', 'manager', 'Sales', 'Sara Director'),

            # HODs
            ('mike_hod', 'password123', 'hod', 'IT', 'Mike HOD'),
            ('lisa_hod', 'password123', 'hod', 'Finance', 'Lisa HOD'),

            # IT Admins
            ('tech_admin', 'password123', 'it_admin', 'IT Inventory', 'Tech Admin'),
            ('inventory_mgr', 'password123', 'it_admin', 'IT Inventory', 'Inventory Manager'),

            # Regular users
            ('alice_sales', 'password123', 'user', 'Sales', 'Alice Sales'),
            ('bob_marketing', 'password123', 'user', 'Marketing', 'Bob Marketing'),
            ('charlie_ops', 'password123', 'user', 'Operations', 'Charlie Ops'),
            ('diana_hr', 'password123', 'user', 'HR', 'Diana HR'),
        ]

        cursor.executemany(
            'INSERT INTO users (username, password, role, department, full_name) VALUES (?, ?, ?, ?, ?)',
            users
        )

        # Generate sample challans with different statuses
        sample_purposes = [
            "New employee onboarding",
            "Device replacement",
            "Project requirement",
            "Field sales team",
            "Client demonstration",
            "Training session",
            "Conference equipment",
            "Backup device",
            "Department expansion",
            "Temporary assignment"
        ]

        departments = ['Sales', 'Marketing', 'Operations', 'HR', 'Finance', 'IT']

        # Generate 20 sample challans with different statuses
        for i in range(1, 21):
            device = random.choice(samsung_devices)
            user = random.choice([u for u in users if u[2] == 'user'])
            purpose = random.choice(sample_purposes)
            serial_number = f"SN{random.randint(1000000000, 9999999999)}"
            quantity = random.randint(1, 5)

            # Create request date in the past 30 days
            request_date = datetime.now() - timedelta(days=random.randint(1, 30))

            # Determine status progression
            status_flow = self._generate_status_flow()

            challan_data = (
                device[0], device[1], serial_number, quantity, purpose, user[0],
                request_date,
                status_flow['manager_status'], status_flow['manager_date'],
                status_flow['hod_status'], status_flow['hod_date'],
                status_flow['it_status'], status_flow['it_date'],
                status_flow['final_status'],
                status_flow['remarks']
            )

            cursor.execute('''
                INSERT INTO challans 
                (device_type, device_model, serial_number, quantity, purpose, requested_by,
                 request_date, manager_status, manager_approval_date, 
                 hod_status, hod_approval_date, it_status, it_approval_date,
                 final_status, remarks)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', challan_data)

        conn.commit()
        conn.close()

        print(f"Database initialized with sample data at {self.db_path}")
        print("Sample users created:")
        for user in users:
            print(f"  - {user[4]} ({user[0]}) - {user[2]} - {user[3]}")

    def _generate_status_flow(self):
        """Generate random status flow for challans"""
        status_options = ['pending', 'approved', 'rejected']
        weights = [0.4, 0.5, 0.1]  # 40% pending, 50% approved, 10% rejected

        manager_status = random.choices(status_options, weights=weights, k=1)[0]
        hod_status = 'pending'
        it_status = 'pending'
        final_status = 'pending'

        manager_date = None
        hod_date = None
        it_date = None
        remarks = None

        if manager_status == 'approved':
            manager_date = datetime.now() - timedelta(days=random.randint(1, 20))
            hod_status = random.choices(status_options, weights=weights, k=1)[0]

            if hod_status == 'approved':
                hod_date = manager_date + timedelta(days=random.randint(1, 5))
                it_status = random.choices(status_options, weights=[0.3, 0.6, 0.1], k=1)[0]

                if it_status == 'approved':
                    it_date = hod_date + timedelta(days=random.randint(1, 3))
                    final_status = 'approved'
                    remarks = "Device ready for allocation"
                elif it_status == 'rejected':
                    it_date = hod_date + timedelta(days=1)
                    final_status = 'rejected'
                    remarks = "Inventory shortage - check back in 2 weeks"
            elif hod_status == 'rejected':
                hod_date = manager_date + timedelta(days=1)
                final_status = 'rejected'
                remarks = "Budget constraints - request denied"
        elif manager_status == 'rejected':
            manager_date = datetime.now() - timedelta(days=random.randint(1, 5))
            final_status = 'rejected'
            remarks = "Not aligned with department goals"

        return {
            'manager_status': manager_status,
            'manager_date': manager_date,
            'hod_status': hod_status,
            'hod_date': hod_date,
            'it_status': it_status,
            'it_date': it_date,
            'final_status': final_status,
            'remarks': remarks
        }

    def create_challan(self, challan_data: Dict[str, Any]) -> int:
        """Create a new challan"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO challans 
            (device_type, device_model, serial_number, quantity, purpose, requested_by)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            challan_data['device_type'],
            challan_data['device_model'],
            challan_data['serial_number'],
            challan_data['quantity'],
            challan_data['purpose'],
            challan_data['requested_by']
        ))

        challan_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return challan_id

    def get_challan_status(self, challan_id: int) -> Optional[Dict[str, Any]]:
        """Get status of a specific challan"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM challans WHERE id = ?', (challan_id,))
        result = cursor.fetchone()
        conn.close()

        if result:
            return dict(result)
        return None

    def update_approval_status(self, challan_id: int, role: str, status: str, remarks: str = None):
        """Update approval status for a specific role"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        approval_date = datetime.now()

        if role == 'manager':
            cursor.execute('''
                UPDATE challans 
                SET manager_status = ?, manager_approval_date = ?, remarks = COALESCE(?, remarks)
                WHERE id = ?
            ''', (status, approval_date, remarks, challan_id))
        elif role == 'hod':
            cursor.execute('''
                UPDATE challans 
                SET hod_status = ?, hod_approval_date = ?, remarks = COALESCE(?, remarks)
                WHERE id = ?
            ''', (status, approval_date, remarks, challan_id))
        elif role == 'it_admin':
            cursor.execute('''
                UPDATE challans 
                SET it_status = ?, it_approval_date = ?, final_status = ?, remarks = COALESCE(?, remarks)
                WHERE id = ?
            ''', (status, approval_date, status, remarks, challan_id))

        conn.commit()
        conn.close()

    def get_all_challans(self, username: str = None) -> List[Dict[str, Any]]:
        """Get all challans, optionally filtered by user"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        if username:
            cursor.execute('SELECT * FROM challans WHERE requested_by = ? ORDER BY request_date DESC', (username,))
        else:
            cursor.execute('SELECT * FROM challans ORDER BY request_date DESC')

        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results

    def get_pending_approvals(self, role: str) -> List[Dict[str, Any]]:
        """Get challans pending approval for a specific role"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        if role == 'manager':
            cursor.execute('SELECT * FROM challans WHERE manager_status = "pending" ORDER BY request_date DESC')
        elif role == 'hod':
            cursor.execute('''
                SELECT * FROM challans 
                WHERE manager_status = "approved" AND hod_status = "pending" 
                ORDER BY request_date DESC
            ''')
        elif role == 'it_admin':
            cursor.execute('''
                SELECT * FROM challans 
                WHERE manager_status = "approved" AND hod_status = "approved" AND it_status = "pending" 
                ORDER BY request_date DESC
            ''')

        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results

    def get_available_devices(self) -> List[Dict[str, Any]]:
        """Get list of available Samsung devices"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(
            'SELECT DISTINCT device_type, device_model, category FROM devices ORDER BY device_type, device_model')
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results

    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user information by username"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        result = cursor.fetchone()
        conn.close()

        if result:
            return dict(result)
        return None


# Singleton instance for easy access
db = ChallanDatabase()


# Test function to verify database setup
def test_database():
    """Test function to verify database is working correctly"""
    print("\n=== Database Test ===\n")

    # Test getting all challans
    all_challans = db.get_all_challans()
    print(f"Total challans in database: {len(all_challans)}")

    # Show some sample challans
    print("\nSample challans:")
    for i, challan in enumerate(all_challans[:3], 1):
        print(f"{i}. Challan ID: {challan['id']}")
        print(f"   Device: {challan['device_model']}")
        print(f"   Status: {challan['final_status']}")
        print(f"   Requested by: {challan['requested_by']}")
        print(f"   Manager: {challan['manager_status']}")
        print(f"   HOD: {challan['hod_status']}")
        print(f"   IT: {challan['it_status']}")
        print()

    # Test pending approvals
    pending_manager = db.get_pending_approvals('manager')
    pending_hod = db.get_pending_approvals('hod')
    pending_it = db.get_pending_approvals('it_admin')

    print(f"Pending Manager approvals: {len(pending_manager)}")
    print(f"Pending HOD approvals: {len(pending_hod)}")
    print(f"Pending IT approvals: {len(pending_it)}")

    # Test available devices
    devices = db.get_available_devices()
    print(f"\nAvailable Samsung devices: {len(devices)} models")
    for device in devices[:5]:  # Show first 5 devices
        print(f"  - {device['device_type'].title()}: {device['device_model']} ({device['category']})")


if __name__ == "__main__":
    test_database()