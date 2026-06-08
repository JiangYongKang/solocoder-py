from __future__ import annotations


class CouponError(Exception):
    pass


class CouponExpiredError(CouponError):
    pass


class CouponMutexError(CouponError):
    def __init__(self, coupon_a_id: str, coupon_b_id: str, group: str) -> None:
        self.coupon_a_id = coupon_a_id
        self.coupon_b_id = coupon_b_id
        self.group = group
        super().__init__(
            f"Coupons '{coupon_a_id}' and '{coupon_b_id}' are mutually exclusive "
            f"in group '{group}'"
        )


class DuplicateCouponError(CouponError):
    def __init__(self, coupon_id: str) -> None:
        self.coupon_id = coupon_id
        super().__init__(f"Duplicate coupon id: '{coupon_id}'")


class InvalidCouponError(CouponError):
    pass
