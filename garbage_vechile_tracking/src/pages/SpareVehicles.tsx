import { SpareVehicleManagement } from '@/components/SpareVehicleManagement';
import { PageHeader } from '@/components/PageHeader';
import { Truck } from 'lucide-react';

const SpareVehicles = () => {
  return (
    <div className="container mx-auto px-4 py-6 space-y-6">
      <PageHeader
        category="Fleet"
        title="Spare Vehicles"
        description="Manage spare vehicles and breakdown replacements"
        icon={Truck}
      />
      <SpareVehicleManagement />
    </div>
  );
};

export default SpareVehicles;
