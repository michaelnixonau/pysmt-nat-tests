; Validity of x + y >= x for x, y in Nat
; we check by asserting the neg.: x + y < x
(declare-const x Nat)
(declare-const y Nat)
(assert (< (+ x y) x))
