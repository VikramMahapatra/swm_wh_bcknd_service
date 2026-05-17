import { useState, useEffect } from "react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/PageHeader";
import { useNavigate } from "react-router-dom";

// Placeholder for IoT data fetching
const fetchCollectionData = async () => {
  // Replace with actual API call to fetch today's collection ton data
  return [
    { zone: "Zone 1", vehicle: "Truck 12", weight: 2.5 },
    { zone: "Zone 2", vehicle: "Truck 22", weight: 3.1 },
    { zone: "Zone 3", vehicle: "Truck 33", weight: 1.8 },
  ];
};

const CollectionTonToday = () => {
  const navigate = useNavigate();
  const [collectionData, setCollectionData] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchCollectionData().then(data => {
      setCollectionData(data);
      setLoading(false);
    });
  }, []);

  return (
    <div className="container mx-auto px-4 py-6 space-y-6">
      <PageHeader
        category="Operations"
        title="Today's Collection (Ton)"
        description="Live garbage collection tonnage from secondary vehicles in each zone."
        actions={
          <Button variant="ghost" size="icon" onClick={() => navigate("/")}>Back</Button>
        }
      />
      <Card className="p-4">
        {loading ? (
          <div className="flex items-center justify-center min-h-[40vh]">
            <span className="text-lg text-muted-foreground">Loading collection data...</span>
          </div>
        ) : (
          <table className="min-w-full divide-y divide-gray-200">
            <thead>
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Zone</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Vehicle</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Weight (Ton)</th>
              </tr>
            </thead>
            <tbody>
              {collectionData.map((item, idx) => (
                <tr key={idx}>
                  <td className="px-6 py-4 whitespace-nowrap">{item.zone}</td>
                  <td className="px-6 py-4 whitespace-nowrap">{item.vehicle}</td>
                  <td className="px-6 py-4 whitespace-nowrap font-bold text-success">{item.weight}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  );
};

export default CollectionTonToday;
