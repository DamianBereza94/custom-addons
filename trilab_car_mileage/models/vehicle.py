from odoo import fields, models, api
from odoo.exceptions import ValidationError
from re import compile

LICENSE_PLATE = compile(r"^[A-Z]{2,3}[A-Z0-9]{4,5}$")


class Vehicle(models.Model):
    """
    A model to manage vehicle registrations.
    Access to vehicle models is restricted based on user roles: vehicles users can only access their own vehicles,
    while administrators can access all vehicle models.
    """

    _name = "vehicle.model"
    _description = "Vehicle Model"

    name = fields.Char(
        string="Registration Number",
        required=True,
        help="The unique registration number of the vehicle. Should consist of uppercase letters (A-Z), "
        "numbers (0-9), and hyphens only, with a maximum length of 15 characters.",
    )
    active = fields.Boolean(default=True, help="Indicates whether the vehicle is active or inactive within the fleet.")
    vehicle_type = fields.Selection(
        [
            ("lte9", "Car engine capacity ≤ 900cc"),
            ("gt9", "Car engine capacity > 900cc"),
            ("mb", "Motorbike"),
            ("sct", "Scooter"),
        ],
        string="Vehicle Type",
        required=True,
        help="The type of the vehicle. Selection options include vehicles based on engine capacity and type.",
    )
    user_ids = fields.Many2many(
        "res.users",
        string="Owners",
        help="Designates the vehicle's owners. Only modifiable by administrators.",
    )
    mileage_ids = fields.One2many(
        "mileage.model", "vehicle_id", string="Mileage Records", help="Records of the vehicle's mileage over time."
    )

    @api.constrains("name")
    def _check_registration_number(self):
        """
        Validates the format and uniqueness of the vehicle's registration number within the system.

        The registration number must:
        - Start with 2 or 3 uppercase letters indicating the region of registration.
        - Followed by 4 or 5 alphanumeric characters (letters and/or numbers),
        making up a total length of 7 or 8 characters.

        This method ensures that the registration number adheres to the Polish vehicle registration number format and
        is unique across all existing vehicle records in the system.
        """
        license_plate = compile(r"^[A-Z]{2,3}[A-Z0-9]{4,5}$")
        if not license_plate.match(self.name):
            raise ValidationError(
                "The registration number is invalid. It must start with 2 or 3 uppercase letters followed by 4 "
                "or 5 alphanumeric characters."
            )

        if self.search_count([("name", "=", self.name), ("id", "!=", self.id)], limit=1):
            raise ValidationError("This registration number already exists. Please enter a unique one.")

    def assign_users(self, include_self=True):
        """
        Updates the car owners' user group. If include_self is True, current users are included in the update.
        This method is used for adding, editing and removing existing records.
        """
        user_ids_to_process = set(self.user_ids.ids) if include_self else set()

        user_ids_to_process.update(self.search_fetch([('id', '!=', self.id)], ['user_ids']).user_ids.ids)

        self.env.ref("trilab_car_mileage.group_car_owners").write({"users": [(6, 0, list(user_ids_to_process))]})

    def unlink(self):
        """
        Overrides the unlink method to update the vehicle owners' user group before deletion of the vehicle record.
        """
        self.assign_users(include_self=False)
        return super().unlink()

    def write(self, vals):
        """
        Overrides the write method to update the vehicle owners' user group whenever vehicle records are updated.
        """
        self.assign_users()
        return super().write(vals)

    @api.model_create_multi
    def create(self, vals_list):
        """
        Overrides the create method to update the vehicle owners' user group after a new vehicle record is created.
        """
        rec = super().create(vals_list)
        rec.assign_users()
        return rec

    def open_mileage_records_report_view(self):
        """
        Returns an action to open the view for mileage records associated with this vehicle.
        """
        return {
            'type': 'ir.actions.act_window',
            'name': 'Mileage Record',
            'view_mode': 'tree',
            'res_model': 'mileage.model',
            'target': 'current',
            'domain': [('vehicle_id', '=', self.id)],
        }
