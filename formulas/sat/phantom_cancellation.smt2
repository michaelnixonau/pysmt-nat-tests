(declare-const x Nat)
(assert (> x 5))
(assert (= (+ (- 2 x) x) 2))
(check-sat)