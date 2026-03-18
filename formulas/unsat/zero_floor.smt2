(declare-const x Nat)
(assert (< x 10))
(assert (= (- x 10) 0))
(check-sat)