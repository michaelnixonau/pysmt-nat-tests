(declare-const x Nat)
(declare-const y Nat)
(assert (= (- x y) (- y x)))
(check-sat)