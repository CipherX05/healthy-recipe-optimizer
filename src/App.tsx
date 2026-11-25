import Nav from '@/sections/Nav';
import Hero from '@/sections/Hero';
import Problem from '@/sections/Problem';
import Pipeline from '@/sections/Pipeline';
import Method from '@/sections/Method';
import Optimizer from '@/sections/Optimizer';
import Deliverables from '@/sections/Deliverables';
import References from '@/sections/References';
import Footer from '@/sections/Footer';

export default function App() {
  return (
    <div className="min-h-screen">
      <Nav />
      <main>
        <Hero />
        <Problem />
        <Pipeline />
        <Method />
        <Optimizer />
        <Deliverables />
        <References />
      </main>
      <Footer />
    </div>
  );
}
