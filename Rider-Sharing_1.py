import uuid
import random
import json

class User:
    """Abstract class for User."""
    def __init__(self, first_name, last_name, contact):
        self._id = str(uuid.uuid4())  # Unique ID
        self._first_name = first_name
        self._last_name = last_name
        self._contact = contact
        self._email = self._generate_email()  # Auto-generated email
        self._password = self._generate_password()  # Auto-generated password

    def _generate_email(self):
        """Generate a unique email address using first and last names."""
        cleaned_first = ''.join(e for e in self._first_name.lower() if e.isalnum())
        cleaned_last = ''.join(e for e in self._last_name.lower() if e.isalnum())
        return f"{cleaned_first}.{cleaned_last}{random.randint(1000, 9999)}@rideshare.com"

    @staticmethod
    def _generate_password():
        """Generate a random password for the user."""
        return f"pass{random.randint(1000, 9999)}"

    def get_user_details(self):
        """Return a dictionary containing user details."""
        return {
            "id": self._id,
            "first_name": self._first_name,
            "last_name": self._last_name,
            "contact": self._contact,
            "email": self._email,
            "password": self._password  # Include password for authentication
        }

    def save_to_file(self, filename):
        """Save the user details to a JSON file."""
        try:
            with open(filename, "r") as file:
                records = json.load(file)
        except (FileNotFoundError, json.JSONDecodeError):
            records = []

        if not isinstance(records, list):
            print("Error: Corrupted data in the file. Resetting records.")
            records = []

        if any(record.get("email") == self._email for record in records):
            print("Error: A user with this email already exists.")
            return

        records.append(self.get_user_details())
        with open(filename, "w") as file:
            json.dump(records, file, indent=4)

from datetime import datetime

class Passenger(User):
    def __init__(self, first_name, last_name, contact):
        super().__init__(first_name, last_name, contact)
        self.__trip_ids = []  # Trip IDs (references in trips.json)

    def book_trip(self, trip, group_size, payment_method):
        """Book a trip for the passenger with group size."""
        total_fare = trip.add_passenger(self, group_size)
        if total_fare is not None:
            payment = Payment(trip, payment_method)
            payment.process_payment()
            trip.save_to_file()
            print("\nTrip booked successfully!")
            print(
                f"  - Route: {trip.route}\n"
                f"  - Distance: {trip.distance} km\n"
                f"  - Group Size: {group_size}\n"
                f"  - Estimated Fare: {total_fare} PHP\n"
                f"  - Driver: {trip.driver._first_name} {trip.driver._last_name}\n"
                f"  - Payment Method: {payment_method}\n"
                f"  - Start Time: {trip.start_time}"
            )
        else:
            print("Booking failed due to insufficient seats.")

    def profile(self):
        """Return the profile details of the passenger."""
        try:
            with open("trips.json", "r") as file:
                trips = json.load(file)
        except (FileNotFoundError, json.JSONDecodeError):
            trips = []

        completed_trips = [
            trip for trip in trips
            if any(p.get("passenger_id") == self._id for p in trip.get("passenger_groups", []))
            and trip.get("status") == "completed"
        ]

        pending_trips = [
            trip for trip in trips
            if any(p.get("passenger_id") == self._id for p in trip.get("passenger_groups", []))
            and trip.get("status") == "pending"
        ]

        return (
            f"Passenger Profile:\n"
            f"  - ID: {self._id}\n"
            f"  - Name: {self._first_name} {self._last_name}\n"
            f"  - Contact: {self._contact}\n"
            f"  - Email: {self._email}\n"
            f"  - Trips Taken: {len(completed_trips)}\n"
            f"  - Pending Trips: {len(pending_trips)}\n"
        )

    def get_trip_history(self):
        """Fetch all trips for this passenger."""
        try:
            with open("trips.json", "r") as file:
                trips = json.load(file)
        except (FileNotFoundError, json.JSONDecodeError):
            return "No trips booked yet."

        passenger_trips = [trip for trip in trips if trip["passenger_id"] == self._id]

        if not passenger_trips:
            return "No trips booked yet."

        return "\n".join(
            f"Trip {idx + 1}:\n"
            f"  - Route: {trip['route']}\n"
            f"  - Distance: {trip['distance']} km\n"
            f"  - Fare: {trip['fare']} PHP\n"
            f"  - Status: {trip['status']}\n"
            for idx, trip in enumerate(passenger_trips)
        )

class Driver(User):
    def __init__(self, first_name, last_name, contact, vehicle):
        super().__init__(first_name, last_name, contact)
        self._vehicle = vehicle
        self._pending_trip_ids = []
        self._in_progress_trip_ids = []  # New attribute
        self._completed_trip_ids = []
        self._canceled_trip_ids = []
        self._total_earnings = 0
        self.available_seats = 4  # Default seat capacity



    def get_vehicle(self):
        """Expose the vehicle object."""
        return self._vehicle

    def add_pending_trip(self, trip):
        """Add a trip to the pending trips list and save the driver data."""
        if trip.trip_id not in self._pending_trip_ids:
            self._pending_trip_ids.append(trip.trip_id)
        self.save_to_file("drivers.json")  # Save updated driver details


    def _sync_pending_trips(self):
        """Synchronize driver's pending trips with trips.json."""
        try:
            with open("trips.json", "r") as file:
                trips = json.load(file)
        except (FileNotFoundError, json.JSONDecodeError):
            return

        self._pending_trip_ids = [
            trip["trip_id"] for trip in trips
            if trip["driver_id"] == self._id and trip["status"] == "pending"
        ]

    def get_pending_trips(self):
        """Fetch all pending trips for this driver from trips.json."""
        try:
            with open("trips.json", "r") as file:
                trips = json.load(file)
        except (FileNotFoundError, json.JSONDecodeError):
            return []

        pending_trips = []
        for trip in trips:
            if trip["driver_id"] == self._id and trip["status"] == "pending":
                # Reconstruct passenger groups
                passenger_groups = [
                    {"passenger_id": group["passenger_id"], "group_size": group["group_size"]}
                    for group in trip.get("passenger_groups", [])
                ]
                # Rebuild the trip object
                new_trip = Trip(trip["route"], trip["distance"], self)
                new_trip.trip_id = trip["trip_id"]
                new_trip.passenger_groups = passenger_groups
                new_trip.available_seats = trip["available_seats"]
                new_trip.status = trip["status"]
                pending_trips.append(new_trip)

        return pending_trips

    def get_in_progress_trips(self):
        """Fetch all in-progress trips for this driver from trips.json."""
        try:
            with open("trips.json", "r") as file:
                trips = json.load(file)
        except (FileNotFoundError, json.JSONDecodeError):
            return []

        in_progress_trips = []
        for trip in trips:
            if trip["driver_id"] == self._id and trip["status"] == "in-progress":
                passenger_groups = [
                    {"passenger_id": group["passenger_id"], "group_size": group["group_size"]}
                    for group in trip.get("passenger_groups", [])
                ]
                new_trip = Trip(trip["route"], trip["distance"], self)
                new_trip.trip_id = trip["trip_id"]
                new_trip.passenger_groups = passenger_groups
                new_trip.available_seats = trip["available_seats"]
                new_trip.status = trip["status"]
                new_trip.final_fare = trip.get("final_fare")
                in_progress_trips.append(new_trip)

        return in_progress_trips



    def _fetch_passenger(self, passenger_id):
        """Fetch passenger details based on passenger ID."""
        try:
            with open("passengers.json", "r") as file:
                passengers = json.load(file)
        except (FileNotFoundError, json.JSONDecodeError):
            return None

        for passenger in passengers:
            if passenger["id"] == passenger_id:
                reconstructed_passenger = Passenger(
                    passenger["first_name"], passenger["last_name"], passenger["contact"]
                )
                reconstructed_passenger._id = passenger["id"]
                return reconstructed_passenger
        return None

    def start_trip(self, trip_id):
        """Start a trip and mark it as in-progress."""
        try:
            with open("trips.json", "r") as file:
                trips = json.load(file)
        except (FileNotFoundError, json.JSONDecodeError):
            print("No trips found.")
            return

        for trip in trips:
            if trip["trip_id"] == trip_id and trip["status"] == "pending":
                trip["status"] = "in-progress"

                # Update driver's trip lists
                if trip_id in self._pending_trip_ids:
                    self._pending_trip_ids.remove(trip_id)
                if trip_id not in self._in_progress_trip_ids:
                    self._in_progress_trip_ids.append(trip_id)

                # Save updated trips
                with open("trips.json", "w") as file:
                    json.dump(trips, file, indent=4)

                # Save updated driver state
                self.save_to_file()
                print(f"Trip {trip_id} started successfully.")
                return

        print("Trip not found or already in progress.")






    def end_trip(self, trip_id):
        """Mark a trip as completed and update earnings."""
        try:
            with open("trips.json", "r") as file:
                trips = json.load(file)
        except (FileNotFoundError, json.JSONDecodeError):
            print("No trips found.")
            return

        for trip in trips:
            if trip["trip_id"] == trip_id and trip["status"] == "in-progress":
                trip["status"] = "completed"

                # Finalize fare and update driver's earnings
                final_fare = trip.get("final_fare") or sum(
                    trip["base_fare"] * group["group_size"] for group in trip["passenger_groups"]
                )
                trip["final_fare"] = final_fare
                self._total_earnings += final_fare  # Update total earnings

                # Update driver's lists
                if trip_id in self._in_progress_trip_ids:
                    self._in_progress_trip_ids.remove(trip_id)
                if trip_id not in self._completed_trip_ids:
                    self._completed_trip_ids.append(trip_id)

                # Save updated trips
                with open("trips.json", "w") as file:
                    json.dump(trips, file, indent=4)

                # Persist driver data
                self.save_to_file("drivers.json")  # Make sure it saves the updated earnings
                print(f"Trip {trip_id} completed. Final Fare: {final_fare:.2f} PHP.")
                return

        print("Trip not found or already completed.")











    def save_to_file(self, filename="drivers.json"):
        """Safely update driver details in the JSON file without overwriting existing data."""
        try:
            with open(filename, "r") as file:
                drivers = json.load(file)
        except (FileNotFoundError, json.JSONDecodeError):
            drivers = []

        # Look for the driver in the existing data
        for i, driver in enumerate(drivers):
            if driver["id"] == self._id:
                # Update the driver's details while preserving specific fields
                updated_driver = self.get_user_details()
                total_earnings = driver.get("total_earnings", 0) + self._total_earnings  # Accumulate total earnings
                updated_driver["total_earnings"] = total_earnings

                # Merge trip lists to prevent duplicates while ensuring updated details are persisted
                drivers[i] = {
                    **driver,  # Preserve existing data
                    **updated_driver,  # Update with the latest details
                    "pending_trip_ids": list(set(driver.get("pending_trip_ids", []) + self._pending_trip_ids)),
                    "in_progress_trip_ids": list(set(driver.get("in_progress_trip_ids", []) + self._in_progress_trip_ids)),
                    "completed_trip_ids": list(set(driver.get("completed_trip_ids", []) + self._completed_trip_ids)),
                    "canceled_trip_ids": list(set(driver.get("canceled_trip_ids", []) + self._canceled_trip_ids)),
                }
                break
        else:
            # If the driver is not found, append the new driver data
            drivers.append(self.get_user_details())

        # Write the updated driver data back to the file    
        with open(filename, "w") as file:
            json.dump(drivers, file, indent=4)










    def get_user_details(self): 
        """Return driver details."""
        return {
            "id": self._id,
            "first_name": self._first_name,
            "last_name": self._last_name,
            "contact": self._contact,
            "email": self._email,
            "password": self._password,
            "vehicle_details": self._vehicle.get_vehicle_details(),
            "pending_trip_ids": self._pending_trip_ids,
            "in_progress_trip_ids": self._in_progress_trip_ids,  # Include in-progress trips
            "completed_trip_ids": self._completed_trip_ids,
            "canceled_trip_ids": self._canceled_trip_ids,
            "total_earnings": self._total_earnings,
            "available_seats": self.available_seats
        }



    def profile(self):
        """Return the profile details of the driver."""
        try:
            with open("drivers.json", "r") as file:
                drivers = json.load(file)
            driver_data = next(d for d in drivers if d["id"] == self._id)
            canceled_trips = len(driver_data.get("canceled_trip_ids", []))
        except (FileNotFoundError, json.JSONDecodeError, StopIteration):
            canceled_trips = 0

        return (
            f"Driver Profile:\n"
            f"  - ID: {self._id}\n"
            f"  - Name: {self._first_name} {self._last_name}\n"
            f"  - Contact: {self._contact}\n"
            f"  - Email: {self._email}\n"
            f"  - Vehicle: {self._vehicle.model} ({self._vehicle.color} - {self._vehicle.license_plate})\n"
            f"  - Pending Trips: {len(self._pending_trip_ids)}\n"
            f"  - Completed Trips: {len(self._completed_trip_ids)}\n"
            f"  - Canceled Trips: {canceled_trips}\n"
            f"  - Total Earnings: {self._total_earnings} PHP\n"
        )

import random

class Vehicle:
    def __init__(self, license_plate, model, color):
        self.license_plate = license_plate
        self.model = model
        self.color = color

    @staticmethod
    def generate_vehicle():
        """Generate a random vehicle."""
        license_plate = f"{random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ')}{random.randint(1000, 9999)}"
        model = random.choice(["Toyota", "Honda", "Ford", "Tesla", "Chevrolet"])
        color = random.choice(["Red", "Blue", "Black", "White", "Gray"])
        return Vehicle(license_plate, model, color)

    def get_vehicle_details(self):
        """Return a dictionary of vehicle details."""
        return {
            "license_plate": self.license_plate,
            "model": self.model,
            "color": self.color
        }

class Trip:
    def __init__(self, route, distance, driver):
        self.trip_id = str(uuid.uuid4())
        self.route = route
        self.distance = distance
        self.base_fare = self.calculate_base_fare(distance)
        self.driver = driver
        self.passenger_groups = []
        self.available_seats = driver.available_seats  # Get seats from the driver
        self.start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.status = "pending"
        self.final_fare = None


    @staticmethod
    def calculate_base_fare(distance):
        """Calculate the base fare for the trip."""
        base_fare = 50
        return base_fare + (distance * 10)

    def has_room_for(self, group_size):
        """Prevent exceeding seat capacity."""
        if self.available_seats - group_size < 0:
            print(f"Error: Not enough seats available for {group_size} passengers.")
            return False
        return True

    def add_passenger(self, passenger, group_size):
        """Add a passenger and group size to the trip."""
        if self.has_room_for(group_size):
            total_fare = self.base_fare * group_size
            self.passenger_groups.append({"passenger_id": passenger._id, "group_size": group_size})
            self.available_seats -= group_size

            # Update driver's available seats
            self.driver.available_seats = self.available_seats
            self.driver.save_to_file("drivers.json")

            # Safely update trips.json
            try:
                with open("trips.json", "r") as file:
                    trips = json.load(file)
            except (FileNotFoundError, json.JSONDecodeError):
                trips = []  # Initialize empty list if the file doesn't exist or is corrupted

            for trip in trips:
                if trip["trip_id"] == self.trip_id:
                    trip["available_seats"] = self.available_seats

            with open("trips.json", "w") as file:
                json.dump(trips, file, indent=4)

            print(
                f"Passenger {passenger._first_name} {passenger._last_name} "
                f"added with {group_size} seat(s). Estimated fare: {total_fare} PHP."
            )
            return total_fare
        return None

    def cancel_trip(self, passenger):
        """Cancel a trip and update related data for the given passenger."""
        if self.status == "completed":
            print(f"Error: Cannot cancel a completed trip {self.trip_id}.")
            return False

        # Remove the passenger from the trip
        updated_groups = [
            group for group in self.passenger_groups
            if group["passenger_id"] != passenger._id
        ]
        if len(updated_groups) == len(self.passenger_groups):
            print(f"Error: Passenger {passenger._first_name} {passenger._last_name} not part of this trip.")
            return False

        self.passenger_groups = updated_groups
        self.available_seats += sum(group["group_size"] for group in updated_groups)

        if not self.passenger_groups:  # Cancel the trip entirely if no passengers remain
            self.status = "canceled"
            if self.trip_id not in self.driver._canceled_trip_ids:
                self.driver._canceled_trip_ids.append(self.trip_id)
            print(f"Trip {self.trip_id} canceled as no passengers remain.")

        # Persist changes
        self.driver.available_seats = self.available_seats
        self.driver.save_to_file("drivers.json")
        self.save_to_file()
        return True









    def finalize_fare(self):
        """Calculate and finalize the total fare when the trip ends."""
        self.final_fare = sum(self.base_fare * group["group_size"] for group in self.passenger_groups)
        return self.final_fare


    def get_trip_details(self):
        """Return trip details as a dictionary."""
        return {
            "trip_id": self.trip_id,
            "route": self.route,
            "distance": self.distance,
            "base_fare": self.base_fare,
            "driver_id": self.driver._id,
            "passenger_groups": self.passenger_groups,  # Use the updated consistent format
            "available_seats": self.available_seats,
            "start_time": self.start_time,
            "status": self.status,
            "final_fare": self.final_fare,
        }



    def save_to_file(self, filename="trips.json"):
        """Ensure all trip details are saved and synchronized."""
        try:
            with open(filename, "r") as file:
                trips = json.load(file)
        except (FileNotFoundError, json.JSONDecodeError):
            trips = []  # Initialize an empty list if the file doesn't exist or is corrupted

        # Update the trip list, ensuring no duplicates
        updated_trips = [trip for trip in trips if trip["trip_id"] != self.trip_id]
        updated_trips.append(self.get_trip_details())

        # Write the updated trips to the file
        with open(filename, "w") as file:
            json.dump(updated_trips, file, indent=4)




class Payment:
    def __init__(self, trip, payment_method):
        self.trip = trip  # Trip object
        self.payment_method = payment_method  # Payment method (e.g., GCash)
        self.payment_status = "Pending"  # Default status

    def process_payment(self):
        """Process the payment."""
        self.payment_status = "Completed"
        print(f"Payment processed successfully via {self.payment_method}")

    def get_payment_details(self):
        """Return payment details."""
        return {
            "trip": self.trip.get_trip_details(),
            "payment_method": self.payment_method,
            "payment_status": self.payment_status
        }

class Menu:
    @classmethod
    def general_menu(cls):
        """General menu for login and signup."""
        while True:
            cls.display_motivation()  # Show motivational quote before the menu appears
            print("\n--- General Menu ---")
            print("1. Login")
            print("2. Sign Up")
            print("3. Exit")
            choice = input("Enter your choice: ")

            if choice == "1":
                email = input("Enter your email: ")
                password = input("Enter your password: ")
                user_type, user = cls.authenticate_user(email, password)

                if user_type == "passenger":
                    print("\nLogin successful! Redirecting to Passenger Menu...")
                    cls.passenger_menu(user)
                elif user_type == "driver":
                    print("\nLogin successful! Redirecting to Driver Menu...")
                    cls.driver_menu(user)
                else:
                    print("\nInvalid email or password. Please try again.")

            elif choice == "2":
                cls.sign_up_menu()

            elif choice == "3":
                print("Exiting...")
                break

            else:
                print("Invalid choice. Please try again.")

    @staticmethod
    def sign_up_menu():
        """Sign-Up menu for registering as Passenger or Driver."""
        print("\n--- Sign Up Menu ---")
        print("1. Sign Up as Passenger")
        print("2. Sign Up as Driver")
        choice = input("Enter your choice: ")

        if choice == "1":
            first_name = input("Enter your first name: ")
            last_name = input("Enter your last name: ")
            contact = input("Enter your contact: ")
            passenger = Passenger(first_name, last_name, contact)
            passenger.save_to_file("passengers.json")
            print(f"\nPassenger created successfully!")
            print(f"Email: {passenger._email}")
            print(f"Password: {passenger._password}")

        elif choice == "2":
            first_name = input("Enter your first name: ")
            last_name = input("Enter your last name: ")
            contact = input("Enter your contact: ")

            # Auto-generate a vehicle
            vehicle = Vehicle.generate_vehicle()
            print("\nAuto-Generated Vehicle Details:")
            print(f"License Plate: {vehicle.license_plate}")
            print(f"Model: {vehicle.model}")
            print(f"Color: {vehicle.color}")

            driver = Driver(first_name, last_name, contact, vehicle)
            driver.save_to_file("drivers.json")
            print(f"\nDriver created successfully!")
            print(f"Email: {driver._email}")
            print(f"Password: {driver._password}")

        else:
            print("Invalid choice. Returning to General Menu.")

    @staticmethod
    def authenticate_user(email, password):
        """Authenticate user credentials and determine user type."""
        try:
            # Load passengers
            with open("passengers.json", "r") as file:
                passengers = json.load(file)
                for passenger_data in passengers:
                    if passenger_data["email"] == email and passenger_data["password"] == password:
                        passenger = Passenger(
                            passenger_data["first_name"],
                            passenger_data["last_name"],
                            passenger_data["contact"]
                        )
                        # Restore passenger details
                        passenger._id = passenger_data["id"]
                        passenger._email = passenger_data["email"]
                        passenger._password = passenger_data["password"]
                        passenger.__trip_ids = passenger_data.get("trip_ids", [])
                        return "passenger", passenger

            # Load drivers
            with open("drivers.json", "r") as file:
                drivers = json.load(file)
                for driver_data in drivers:
                    if driver_data["email"] == email and driver_data["password"] == password:
                        # Ensure vehicle details exist
                        vehicle_details = driver_data.get("vehicle_details", {})
                        if not vehicle_details:
                            print("Error: Driver data is incomplete or corrupted.")
                            return None, None

                        # Reconstruct the Vehicle
                        vehicle = Vehicle(
                            vehicle_details.get("license_plate", "UNKNOWN"),
                            vehicle_details.get("model", "UNKNOWN"),
                            vehicle_details.get("color", "UNKNOWN")
                        )

                        # Reconstruct the Driver
                        driver = Driver(
                            driver_data["first_name"],
                            driver_data["last_name"],
                            driver_data["contact"],
                            Vehicle(
                                driver_data["vehicle_details"]["license_plate"],
                                driver_data["vehicle_details"]["model"],
                                driver_data["vehicle_details"]["color"]
                            )
                        )
                        # Restore driver attributes
                        driver._id = driver_data["id"]
                        driver._email = driver_data["email"]
                        driver._password = driver_data["password"]
                        driver._pending_trip_ids = driver_data.get("pending_trip_ids", [])
                        driver._in_progress_trip_ids = driver_data.get("in_progress_trip_ids", [])
                        driver._completed_trip_ids = driver_data.get("completed_trip_ids", [])
                        driver._canceled_trip_ids = driver_data.get("canceled_trip_ids", [])
                        driver._total_earnings = driver_data.get("total_earnings", 0)  # Restore total earnings
                        driver.available_seats = driver_data.get("available_seats", 4)




                        # Synchronize pending trips for accuracy
                        driver._sync_pending_trips()

                        # Automatically save the driver state back to file on login
                        driver.save_to_file("drivers.json")

                        return "driver", driver

        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error reading user data: {e}")
            return None, None

        return None, None


    @staticmethod
    def find_available_driver():
        """Find an available driver (not currently on a full trip)."""
        try:
            # Load drivers and trips data
            with open("drivers.json", "r") as file:
                drivers = json.load(file)
        except (FileNotFoundError, json.JSONDecodeError):
            print("Error: Driver file not found or corrupted.")
            return None

        try:
            with open("trips.json", "r") as trip_file:
                trips = json.load(trip_file)
        except (FileNotFoundError, json.JSONDecodeError):
            trips = []  # If trips file is empty or not found, assume no trips exist

        # Identify drivers with space in pending trips or with no trips
        for driver_data in drivers:
            driver_id = driver_data["id"]
            vehicle_details = driver_data.get("vehicle_details", {})
            
            # Reconstruct the Driver object
            driver = Driver(
                driver_data["first_name"],
                driver_data["last_name"],
                driver_data["contact"],
                Vehicle(
                    vehicle_details.get("license_plate", "UNKNOWN"),
                    vehicle_details.get("model", "UNKNOWN"),
                    vehicle_details.get("color", "UNKNOWN"),
                ),
            )
            driver._id = driver_id
            driver.__pending_trip_ids = driver_data.get("pending_trip_ids", [])

            # Check if driver has pending trips with available seats
            has_space = True
            for trip in trips:
                if trip["driver_id"] == driver_id and trip["status"] == "pending":
                    if trip["available_seats"] <= 0:
                        has_space = False
                        break  # Fully booked trips

            # If driver has space or no trips at all, return driver
            if has_space:
                return driver

        print("No available drivers found.")
        return None

    @staticmethod
    def _fetch_driver(driver_id):
        """Fetch driver details based on driver ID."""
        try:
            with open("drivers.json", "r") as file:
                drivers = json.load(file)
        except (FileNotFoundError, json.JSONDecodeError):
            return None

        for driver_data in drivers:
            if driver_data["id"] == driver_id:
                vehicle = Vehicle(
                    driver_data["vehicle_details"]["license_plate"],
                    driver_data["vehicle_details"]["model"],
                    driver_data["vehicle_details"]["color"]
                )
                driver = Driver(
                    driver_data["first_name"],
                    driver_data["last_name"],
                    driver_data["contact"],
                    vehicle
                )
                driver._id = driver_data["id"]
                return driver
        return None

    @classmethod
    def motivation_quote_1(cls):
        print("\n🌟 Motivation of the Day 🌟\n"
              "“The road to success is always under construction. Keep moving forward!” 🚀\n")

    @classmethod
    def motivation_quote_2(cls):
        print("\n🌟 Motivation of the Day 🌟\n"
              "“Don’t watch the clock; do what it does. Keep going.” ⏳\n")

    @classmethod
    def motivation_quote_3(cls):
        print("\n🌟 Motivation of the Day 🌟\n"
              "“Small steps every day add up to big success.” 🏃‍♂️💡\n")

    @classmethod
    def motivation_quote_4(cls):
        print("\n🌟 Motivation of the Day 🌟\n"
              "“Believe in yourself and all that you are. You are stronger than you think!” 💪✨\n")

    @classmethod
    def motivation_quote_5(cls):
        print("\n🌟 Motivation of the Day 🌟\n"
              "“Opportunities don’t happen. You create them.” 🌟💼\n")

    @classmethod
    def motivation_quote_6(cls):
        print("\n🌟 Motivation of the Day 🌟\n"
              "“Success doesn’t come to you. You go to it!” 🌠🛤️\n")

    @classmethod
    def display_motivation(cls):
        """Display a random motivation of the day."""
        quotes = [
            cls.motivation_quote_1,
            cls.motivation_quote_2,
            cls.motivation_quote_3,
            cls.motivation_quote_4,
            cls.motivation_quote_5,
            cls.motivation_quote_6,
        ]
        random.choice(quotes)()
    
    @staticmethod
    def passenger_menu(passenger):
        """Menu for passenger-specific operations."""
        while True:
            print("\n--- Passenger Menu ---")
            print("1. Book a Trip")
            print("2. Cancel a Trip")
            print("3. View Trip History")
            print("4. View Profile")
            print("5. Logout")
            choice = input("Enter your choice: ")

            if choice == "1":  # Book a Trip
                route = input("Enter destination: ")
                distance = float(input("Enter distance (in km): "))

                driver = Menu.find_available_driver()
                if not driver:
                    print("No drivers are currently available. Please wait...")
                    continue

                # Prompt for group size
                group_size = int(input("How many passengers (1-4)? "))
                if group_size < 1 or group_size > 4:
                    print("Invalid group size. Please enter a number between 1 and 4.")
                    continue

                payment_method = input("Enter payment method (GCash/PayPal/Debit): ")

                # Create a new trip and book it for the current passenger
                new_trip = Trip(route, distance, driver)
                passenger.book_trip(new_trip, group_size, payment_method)  # Use the logged-in passenger
                driver.add_pending_trip(new_trip)  # Add trip to driver's pending trips

            elif choice == "2":  # Cancel a Trip
                try:
                    with open("trips.json", "r") as file:
                        trips = json.load(file)
                except (FileNotFoundError, json.JSONDecodeError):
                    print("No trips available.")
                    continue

                # Fetch trips where the passenger is part of the group
                passenger_trips = [
                    trip for trip in trips
                    if any(p.get("passenger_id") == passenger._id for p in trip.get("passenger_groups", []))
                    and trip.get("status") in ["pending", "in-progress"]
                ]

                if not passenger_trips:
                    print("You have no trips to cancel.")
                    continue

                # Display the trips available for cancellation
                for idx, trip in enumerate(passenger_trips, 1):
                    print(f"{idx}. Route: {trip['route']}, Distance: {trip['distance']} km, Trip ID: {trip['trip_id']}")

                try:
                    trip_choice = int(input("Enter the number of the trip to cancel: ")) - 1
                    if 0 <= trip_choice < len(passenger_trips):
                        trip_data = passenger_trips[trip_choice]
                        trip_id = trip_data["trip_id"]

                        # Reconstruct the driver
                        driver = Menu._fetch_driver(trip_data["driver_id"])

                        if not driver:
                            print("Error: Driver data for the trip is missing or corrupted.")
                            continue

                        # Reconstruct the trip object with a valid driver
                        current_trip = Trip(trip_data["route"], trip_data["distance"], driver)
                        current_trip.trip_id = trip_id

                        # Safely rebuild passenger groups for the trip
                        current_trip.passenger_groups = [
                            {"passenger_id": group["passenger_id"], "group_size": group["group_size"]}
                            for group in trip_data.get("passenger_groups", [])
                        ]

                        # Use `cancel_trip` instead of `cancel_passenger`
                        if current_trip.cancel_trip(passenger):
                            current_trip.save_to_file()
                            print("Trip canceled successfully.")
                        else:
                            print("Failed to cancel the trip.")
                    else:
                        print("Invalid choice.")
                except ValueError:
                    print("Invalid input. Please enter a number.")


            elif choice == "3":
                print("Trip History:")
                print(passenger.get_trip_history())

            elif choice == "4":
                print(passenger.profile())

            elif choice == "5":
                print("Logging out...")
                break

            else:
                print("Invalid choice. Please try again.")

    @staticmethod
    def driver_menu(driver):
        """Menu for driver-specific operations."""
        while True:
            print("\n--- Driver Menu ---")
            print("1. View Pending Trips")
            print("2. Start a Trip")
            print("3. End Trip")
            print("4. View Profile")
            print("5. Logout")
            choice = input("Enter your choice: ")

            if choice == "1":  # View Pending Trips
                pending_trips = driver.get_pending_trips()
                if not pending_trips:
                    print("No pending trips.")
                else:
                    for idx, trip in enumerate(pending_trips, 1):
                        # Adjusting to correctly access group size
                        total_fare = sum(trip.base_fare * group["group_size"] for group in trip.passenger_groups)
                        passenger_details = ", ".join(
                            f"{driver._fetch_passenger(group['passenger_id'])._first_name} "
                            f"{driver._fetch_passenger(group['passenger_id'])._last_name} "
                            f"({group['group_size']} seat(s))"
                            for group in trip.passenger_groups
                        )
                        print(
                            f"{idx}. Route: {trip.route}, Distance: {trip.distance} km, "
                            f"Total Fare: {total_fare:.2f} PHP, Passengers: {passenger_details} (ID: {trip.trip_id})"
                        )


            elif choice == "2":  # Start a Trip
                pending_trips = driver.get_pending_trips()
                if not pending_trips:
                    print("No pending trips.")
                    continue

                for idx, trip in enumerate(pending_trips, 1):
                    total_fare = sum(trip.base_fare * group["group_size"] for group in trip.passenger_groups)
                    print(
                        f"{idx}. Route: {trip.route}, Distance: {trip.distance} km, "
                        f"Total Fare: {total_fare:.2f} PHP (ID: {trip.trip_id})"
                    )

                try:
                    trip_choice = int(input("Enter the number of the trip to start: ")) - 1
                    if 0 <= trip_choice < len(pending_trips):
                        selected_trip = pending_trips[trip_choice]
                        driver.start_trip(selected_trip.trip_id)
                    else:
                        print("Invalid choice.")
                except ValueError:
                    print("Invalid input. Please enter a number.")

            elif choice == "3":  # End a Trip
                in_progress_trips = driver.get_in_progress_trips()
                if not in_progress_trips:
                    print("No trips currently in progress to end.")
                    continue

                print("\n--- In-Progress Trips ---")
                for idx, trip in enumerate(in_progress_trips, 1):
                    passenger_details = ", ".join(
                        f"{driver._fetch_passenger(group['passenger_id'])._first_name} "
                        f"{driver._fetch_passenger(group['passenger_id'])._last_name} "
                        f"({group['group_size']} seat(s))"
                        for group in trip.passenger_groups
                    )
                    print(
                        f"{idx}. Route: {trip.route}, Distance: {trip.distance} km, "
                        f"Passengers: {passenger_details}, Trip ID: {trip.trip_id}"
                    )

                try:
                    trip_choice = int(input("Enter the number of the trip to end: ")) - 1
                    if 0 <= trip_choice < len(in_progress_trips):
                        selected_trip = in_progress_trips[trip_choice]
                        final_fare = selected_trip.finalize_fare()
                        driver.end_trip(selected_trip.trip_id)
                        print(f"Trip {selected_trip.trip_id} completed successfully. Final Fare: {final_fare:.2f} PHP.")
                        selected_trip.save_to_file()
                    else:
                        print("Invalid choice.")
                except ValueError:
                    print("Invalid input. Please enter a number.")

            elif choice == "4":  # View Profile
                print(driver.profile())

            elif choice == "5":  # Logout
                driver.save_to_file("drivers.json")  # Save the driver state before logout
                print("Logging out...")
                break

            else:
                print("Invalid choice. Please try again.")


import os

def initialize_json_files():
    """Ensure all required JSON files exist."""
    json_files = ["drivers.json", "passengers.json", "trips.json", "in_progress_trips.json"]

    for file_name in json_files:
        if not os.path.exists(file_name):
            with open(file_name, "w") as file:
                json.dump([], file)  # Initialize with an empty list

if __name__ == "__main__":
    print("Welcome to the Ride-Sharing App!")
    Menu.general_menu()
