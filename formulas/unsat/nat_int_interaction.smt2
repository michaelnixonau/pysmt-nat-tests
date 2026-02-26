; Check that Nats and Ints interact correctly
; We set x to be negative Int, and assert that the Nat y is equal to x.
; Should be UNSAT since Nats cannot be negative.
(declare-const x Int)
(declare-const y Nat)
(assert (< x 0))
(assert (= y x))