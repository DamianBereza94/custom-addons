from odoo import fields, models, api
from odoo.exceptions import ValidationError
from re import compile

LICENSE_PLATE = compile(r"^[A-Z]{2,3}[A-Z0-9]{1,5}$")


class Vehicle(models.Model):
    """
    A model to manage vehicle registrations.
    """

    _name = "vehicle.model"
    _description = "Vehicle Model"

    name = fields.Char(
        string="Registration Number", required=True, help="The unique registration number of the vehicle."
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
        help="The type of the vehicle.",
    )
    status = fields.Selection(
        [('in', "In Fleet"), ('off', "Off Fleet")],
        compute='_compute_status',
        help="Current status of the vehicle in the fleet.",
    )
    user_ids = fields.Many2many(
        "res.users", string="Owners", help="Designates the vehicle's owners. Only modifiable by administrators."
    )
    mileage_ids = fields.One2many('mileage.model', 'vehicle_id', string='Mileage Records')

    @api.onchange('active')
    def _compute_status(self):
        """
        Compute status field value based on the 'active' field.
        """
        self.status = 'in' if self.active else 'off'

    @api.constrains("name")
    def _check_registration_number(self):
        """
        Validates the format and uniqueness of the vehicle's registration number within the system.

        The registration number must:
        - Start with 2 or 3 uppercase letters indicating the region of registration.
        - Followed by 4 or 5 alphanumeric characters (letters and/or numbers),
        making up a total length of 7 or 8 characters.
        """
        if not LICENSE_PLATE.match(self.name):
            raise ValidationError(
                "The registration number is invalid. It must start with 2 or 3 uppercase letters followed by 4 "
                "or 5 alphanumeric characters."
            )

        if self.search_count([("name", "=", self.name), ("id", "!=", self.id)], limit=1):
            raise ValidationError("This registration number already exists. Please enter a unique one.")

    def assign_users(self, include_self=True):
        """
        Updates the car owners' user group. If include_self is True, current users are included in the update.
        """
        user_ids_to_process = set(*[rec.user_ids.ids for rec in self]) if include_self else set()

        user_ids_to_process.update(
                *[rec.search_fetch([('id', '!=', rec.id)], ['user_ids']).user_ids.ids for rec in self]
            )

        self.env.ref("trilab_car_mileage.group_car_owners").write({"users": [(6, 0, list(user_ids_to_process))]})

    def unlink(self):
        """
        Overrides the unlink method to update the vehicle owners' user group.
        """
        self.assign_users(include_self=False)
        return super().unlink()

    def write(self, vals):
        """
        Overrides the write method to update the vehicle owners' user group.
        """
        result = super().write(vals)
        self.assign_users()
        return result

    @api.model_create_multi
    def create(self, vals_list):
        """
        Overrides the create method to update the vehicle owners' user group.
        """
        result = super().create(vals_list)
        result.assign_users()
        return result

    def open_mileage_records_report_view(self):
        """
        Returns an action to open the view for mileage records associated with this vehicle.
        """
        return {
            'type': 'ir.actions.act_window',
            'name': 'Register Mileage',
            'view_mode': 'form',
            'views': [
                (self.env.ref('trilab_car_mileage.mileage_model_form_view').id, 'form'),
            ],
            'res_model': 'mileage.model',
            'target': 'new',
            'context': {'default_vehicle_id': self.id},
        }
