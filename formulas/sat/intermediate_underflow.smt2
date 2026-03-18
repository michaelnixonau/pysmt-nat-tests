(declare-const x Nat)
(assert (< x 3))
(assert (= (+ (- x 5) 5) x))
(check-sat)