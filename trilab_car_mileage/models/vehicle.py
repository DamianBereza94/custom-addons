import re

from odoo import fields, models, api
from odoo.exceptions import ValidationError
from re import compile

LICENSE_PLATE = compile(r"^[A-Z0-9\-]{1,15}$")


class Vehicle(models.Model):
    """
    Class Vehicle allowing vehicle registration.
    Internal users can access only their own vehicle models,
    while administrators have access to all vehicle models.
    """

    _name = "vehicle.model"
    _description = "Vehicle Model"

    name = fields.Char(
        string="Registration Number",
        required=True,
        help="Enter the vehicle's unique registration number. It should "
        "consist of 1 to 15 uppercase letters, "
        "numbers, and hyphens.",
    )
    active = fields.Boolean(
        default=True,
        help="Toggle the field to set the vehicle as active or inactive in fleet.",
    )
    vehicle_type = fields.Selection(
        [
            ("lte9", "Car engine capacity below or equal to 900cc"),
            ("gt9", "Car engine capacity above 900cc"),
            ("mb", "Motorbike"),
            ("sct", "Scooter"),
        ],
        string="Vehicle Type",
        required=True,
        help="Select the type of vehicle from the given options.",
    )
    user_ids = fields.Many2many(
        "res.users",
        string="Owner",
        required=True,
        help="Assign app users as the users of the vehicle. Only accessible by administrators.",
    )
    mileage_ids = fields.One2many(
        "mileage.model",
        "vehicle_id",
        string="Mileage Records",
        help="This field contains the mileage records associated with the vehicle.",
    )

    @api.constrains("name")
    def _check_name(self):
        """
        Validates the vehicle's registration number format,
        it must consist of 1 to 15 characters, which can only be uppercase letters, numbers, and hyphens.
        """
        if not LICENSE_PLATE.match(self.name):
            raise ValidationError(
                "The registration number must consist of 1 to 15 characters, including only uppercase letters, "
                "numbers, and hyphens."
            )

        if self.name_search(self.name, [("id", "!=", self.id)], limit=1):
            raise ValidationError(
                "This registration number already exist. Please choose a unique one."
            )

    def assign_users(self, include_self=True):
        """
        Update car owners group users. Include current user_ids in the list if include_self is True.
        This is adaptable for both adding new records and removing existing ones.
        """
        user_ids_to_process = []
        if include_self:
            user_ids_to_process.extend(self.user_ids.ids)

        for record in self:
            other_user_ids = self.env["vehicle.model"].search_fetch([("id", "!=", record.id)], ["user_ids"]).user_ids.ids

            user_ids_to_process.extend(other_user_ids)

        if user_ids_to_process:
            unique_user_ids = list(set(user_ids_to_process))
            self.env.ref("trilab_car_mileage.group_car_owners").write({"users": [(6, 0, unique_user_ids)]})

    def unlink(self):
        """
        Override unlink to update users before deleting the record.
        """
        self.assign_users(include_self=False)
        return super(Vehicle, self).unlink()

    def write(self, vals):
        result = super().write(vals)
        self.assign_users()
        return result

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records.assign_users()
        return records

    def open_mileage_records_report_view(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Mileage Record',
            'view_mode': 'tree',
            'res_model': 'mileage.model',
            'target': 'current',
            'context': {'default_vehicle_id': self.id}
        }