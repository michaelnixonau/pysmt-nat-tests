; Asserting that negative x is actually 0
(declare-const x Nat)
(assert (= x 5))
(assert (= (- x) 0)) 
(check-sat)